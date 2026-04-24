"""
Aylık üretim pipeline: runtime Excel → LCA → temizlik → MILP (PuLP+CBC) → selected_matches.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

_V2_ROOT = Path(__file__).resolve().parent.parent
if str(_V2_ROOT) not in sys.path:
    sys.path.insert(0, str(_V2_ROOT))

from core.config import (
    ENV_SYMBIOSIS_STRICT_MATCHES,
    RUNTIME_DIR,
    allow_self_symbiosis,
)
from core.data_cleaning import clean_matches, clean_optimization_results
from core.matches_ready_builder import ensure_matches_lca_ready
from core.transport_modes import normalize_lca_transport_mode
from core.waste_process_links_generator import try_generate_waste_process_links
from core.lca_client import run_lca_batch_for_matches
from core.resource_templates import (
    apply_lca_totals,
    attach_resource_co2_column,
    join_capacity_and_resource_use,
    load_resource_emission_template,
    load_resource_use_template,
)
from core.period import (
    matches_lca_filename,
    parse_period,
    process_capacity_monthly_filename,
    selected_matches_filename,
    selected_raw_filename,
)
from core.match_derived_metrics import apply_literature_transport_cost, compute_tech_score_series
from core.scoring import recompute_sustainability_scores
from optimization.result_reader import SELECTED_MATCHES_CSV, extract_selected_rows
from pipeline.selected_export import filter_selected_matches
from core.factory_ids import (
    format_factory_id,
    parse_factory_id,
    validate_matches_against_processes_and_streams,
)

logger = logging.getLogger(__name__)


def _as_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _is_auxiliary_row(is_auxiliary: Any) -> bool:
    if is_auxiliary is None or (isinstance(is_auxiliary, float) and pd.isna(is_auxiliary)):
        return False
    if isinstance(is_auxiliary, bool):
        return bool(is_auxiliary)
    s = str(is_auxiliary).strip().lower()
    if s in ("1", "true", "yes", "evet", "aux", "auxiliary"):
        return True
    if s in ("0", "false", "no", "hayır", ""):
        return False
    try:
        return float(s) != 0.0
    except ValueError:
        return False


def auxiliary_process_ids(processes: pd.DataFrame) -> set[str]:
    if processes is None or processes.empty or "process_id" not in processes.columns:
        return set()
    if "is_auxiliary_process" not in processes.columns:
        return set()
    out: set[str] = set()
    for _, row in processes.iterrows():
        if _is_auxiliary_row(row.get("is_auxiliary_process")):
            pid = row.get("process_id")
            if pid is not None and not (isinstance(pid, float) and pd.isna(pid)):
                out.add(str(pid).strip())
    return out


def filter_auxiliary_from_matches(matches: pd.DataFrame, auxiliary_ids: set[str]) -> pd.DataFrame:
    if not auxiliary_ids or matches is None or matches.empty:
        return matches if matches is not None else pd.DataFrame()
    if "process_id" not in matches.columns:
        return matches
    pid = matches["process_id"].astype(str).str.strip()
    return matches.loc[~pid.isin(auxiliary_ids)].copy()


def filter_auxiliary_from_capacity(process_capacity: pd.DataFrame, auxiliary_ids: set[str]) -> pd.DataFrame:
    if not auxiliary_ids or process_capacity is None or process_capacity.empty:
        return process_capacity if process_capacity is not None else pd.DataFrame()
    if "process_id" not in process_capacity.columns:
        return process_capacity
    pid = process_capacity["process_id"].astype(str).str.strip()
    return process_capacity.loc[~pid.isin(auxiliary_ids)].copy()


def apply_waste_kg_min_max(
    monthly_kg: float,
    row: pd.Series,
    *,
    min_col: str = "kg_per_ton_min",
    max_col: str = "kg_per_ton_max",
) -> float:
    lo = _as_float(row.get(min_col), None)
    hi = _as_float(row.get(max_col), None)
    if lo is None or hi is None:
        return float(monthly_kg)
    if lo > hi:
        return float(monthly_kg)
    return float(max(lo, min(float(monthly_kg), hi)))


def apply_waste_coefficient_clipping(
    matches: pd.DataFrame,
    waste_coefficients: Optional[pd.DataFrame],
) -> pd.DataFrame:
    if waste_coefficients is None or waste_coefficients.empty:
        return matches
    if "waste_id" not in matches.columns or "waste_id" not in waste_coefficients.columns:
        return matches
    m = matches.merge(waste_coefficients, on="waste_id", how="left", suffixes=("", "_wc"))
    m["waste_amount_monthly"] = m.apply(
        lambda r: apply_waste_kg_min_max(float(r["waste_amount_monthly"]), r),
        axis=1,
    )
    return m


def compute_waste_amount_monthly_column(
    matches: pd.DataFrame,
    *,
    base_col: str = "waste_amount_base",
    waste_coefficients: Optional[pd.DataFrame] = None,
    scale_fn: Optional[Callable[[pd.Series], float]] = None,
) -> pd.DataFrame:
    df = matches.copy()
    if base_col not in df.columns:
        raise ValueError(f"matches içinde '{base_col}' yok")

    def _scale(row: pd.Series) -> float:
        if scale_fn is None:
            v = _as_float(row.get(base_col), 0.0)
            return float(v or 0.0)
        return float(scale_fn(row))

    df["waste_amount_monthly"] = df.apply(_scale, axis=1).astype(float)
    if waste_coefficients is None or waste_coefficients.empty:
        return df
    if "waste_id" not in df.columns or "waste_id" not in waste_coefficients.columns:
        return df
    m = df.merge(waste_coefficients, on="waste_id", how="left", suffixes=("", "_wc"))
    m["waste_amount_monthly"] = m.apply(
        lambda r: apply_waste_kg_min_max(float(r["waste_amount_monthly"]), r),
        axis=1,
    )
    return m


def placeholder_process_metadata_for_scoring(
    matches: pd.DataFrame,
    process_metadata: Optional[pd.DataFrame],
) -> pd.DataFrame:
    out = matches.copy()
    if process_metadata is None or process_metadata.empty or "process_id" not in out.columns:
        out["metadata_score_penalty"] = 0.0
        out["metadata_score_bonus"] = 0.0
        return out
    if "process_id" not in process_metadata.columns:
        out["metadata_score_penalty"] = 0.0
        out["metadata_score_bonus"] = 0.0
        return out
    meta = process_metadata.drop_duplicates(subset=["process_id"], keep="last")
    merged = out.merge(meta, on="process_id", how="left", suffixes=("", "_pm"))
    merged["metadata_score_penalty"] = 0.0
    merged["metadata_score_bonus"] = 0.0
    return merged


def _read_optional_excel(runtime: Path, name: str) -> Optional[pd.DataFrame]:
    p = runtime / name
    if not p.is_file():
        return None
    return pd.read_excel(p)


def run_monthly_pipeline(
    period: str,
    *,
    triggered_by: str = "api",
    runtime_dir: Optional[Path] = None,
    global_bounds: Optional[dict[str, float]] = None,
    strict_symbiosis_matches: Optional[bool] = None,
) -> dict[str, Any]:
    """
    `outputs/runtime/` altindaki girdilerle aylik uretim.

    **Sıra:** (1) `waste_process_links.xlsx` otomatik üretimi (üç temel dosya varsa),
    (2) `matches_LCA_ready.xlsx` — symbiosis dörtlemesi tam ise otomatik üretilir.
    `SYMBIOSIS_SKIP_WASTE_LINKS_AUTOGEN=1` ile (1) atlanır.

    Ortam: `SYMBIOSIS_STRICT_MATCHES=1` → yalnızca symbiosis dörtlemesi ile üretim zorunlu.
    Varsayılan: self-simbiyoz kapalı. ``SYMBIOSIS_ALLOW_SELF_SYMBIOSIS=1`` ile aynı fabrika içi eşleşmelere izin verilir.

    Gerekli dosyalar (runtime): matches_LCA_ready.xlsx (veya yukarıdaki dört dosya),
    factory_status.xlsx, process_status.xlsx, process_capacity.csv, waste_streams.xlsx,
    capacity_factors.xlsx

    İsteğe bağlı: waste_coefficients.xlsx, process_metadata.xlsx
    """
    runtime = Path(runtime_dir or RUNTIME_DIR)
    runtime.mkdir(parents=True, exist_ok=True)

    try:
        try_generate_waste_process_links(runtime, period)
    except Exception as e:
        logger.exception("waste_process_links üretimi")
        return {"status": "failed", "period": period, "error": f"waste_process_links üretimi: {e}"}

    strict = strict_symbiosis_matches
    if strict is None:
        strict = os.environ.get(ENV_SYMBIOSIS_STRICT_MATCHES, "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    err_ready = ensure_matches_lca_ready(runtime, strict_symbiosis_only=bool(strict))
    if err_ready:
        return {"status": "failed", "period": period, "error": err_ready}

    _, current_month = parse_period(period)

    try:
        matches = pd.read_excel(runtime / "matches_LCA_ready.xlsx")
        factory_status = pd.read_excel(runtime / "factory_status.xlsx")
        process_status = pd.read_excel(runtime / "process_status.xlsx")
        process_capacity = pd.read_csv(runtime / "process_capacity.csv", sep=";", decimal=",")
        waste_streams = pd.read_excel(runtime / "waste_streams.xlsx")
        capacity_factors_df = pd.read_excel(runtime / "capacity_factors.xlsx")
    except Exception as e:
        return {"status": "failed", "period": period, "error": f"Girdi okunamadı: {e}"}

    processes = _read_optional_excel(runtime, "processes.xlsx")
    waste_coeff = _read_optional_excel(runtime, "waste_coefficients.xlsx")
    process_metadata = _read_optional_excel(runtime, "process_metadata.xlsx")

    aux_ids = auxiliary_process_ids(processes) if processes is not None else set()
    matches = filter_auxiliary_from_matches(matches, aux_ids)

    if not allow_self_symbiosis():
        if "source_factory" in matches.columns and "target_factory" in matches.columns:
            _sf = matches["source_factory"].map(parse_factory_id)
            _tf = matches["target_factory"].map(parse_factory_id)
            _keep = ~(_sf.notna() & _tf.notna() & (_sf == _tf))
            _n = (~_keep).sum()
            if _n:
                logger.info("Self-simbiyoz kapalı: %s eşleşme satırı elendi (aynı fabrika).", int(_n))
            matches = matches.loc[_keep].copy()

    matches = matches.merge(
        waste_streams[["waste_id", "physical_state"]],
        on="waste_id",
        how="left",
    )

    for _fc in ("source_factory", "target_factory"):
        if _fc in matches.columns:
            matches[_fc] = matches[_fc].map(parse_factory_id)

    if processes is not None and not processes.empty:
        vfac = validate_matches_against_processes_and_streams(matches, processes, waste_streams)
        for msg in vfac[:25]:
            logger.warning("Fabrika doğrulama: %s", msg)

    def get_capacity_factor(factory_id: Any, month: int) -> float:
        fid = parse_factory_id(factory_id)
        if fid is None:
            return 1.0
        cf_fac = capacity_factors_df["factory_id"].map(parse_factory_id)
        row = capacity_factors_df[
            (cf_fac == fid) & (capacity_factors_df["month"] == month)
        ]
        if row.empty:
            return 1.0
        return float(row["capacity_factor"].values[0])

    process_id_to_factory = matches[["process_id", "target_factory"]].drop_duplicates()
    process_id_to_factory = process_id_to_factory.rename(columns={"target_factory": "factory_id"})
    process_capacity = process_capacity.merge(process_id_to_factory, on="process_id", how="left")

    process_capacity["capacity_ton_per_day"] = (
        process_capacity["capacity_ton_per_day"]
        .astype(str)
        .str.replace(",", ".")
        .str.strip()
        .astype(float)
    )

    def compute_monthly_capacity(row: pd.Series) -> float:
        process_id = row["process_id"]
        factory_id = row["factory_id"]
        base_cap_ton_day = row["capacity_ton_per_day"]
        if pd.isna(factory_id):
            return float(base_cap_ton_day) * 1000 * 30
        fid = parse_factory_id(factory_id)
        if fid is None:
            return float(base_cap_ton_day) * 1000 * 30
        fs_fac = factory_status["factory_id"].map(parse_factory_id)
        f_filter = factory_status[
            (fs_fac == fid) & (factory_status["month"] == current_month)
        ]
        f_status = float(f_filter["status"].values[0]) if not f_filter.empty else 1.0
        p_filter = process_status[
            (process_status["process_id"] == process_id)
            & (process_status["month"] == current_month)
        ]
        p_status = float(p_filter["status"].values[0]) if not p_filter.empty else 1.0
        cap_factor = get_capacity_factor(factory_id, current_month)
        base_cap_kg_month = float(base_cap_ton_day) * 1000 * 30
        return base_cap_kg_month * f_status * p_status * cap_factor

    process_capacity["capacity_monthly"] = process_capacity.apply(compute_monthly_capacity, axis=1)
    process_capacity = filter_auxiliary_from_capacity(process_capacity, aux_ids)

    def compute_monthly_waste(row: pd.Series) -> float:
        base_kg = float(row["waste_amount_base"])
        src_f = row["source_factory"]
        cf = get_capacity_factor(src_f, current_month)
        return base_kg * cf

    matches["waste_amount_monthly"] = matches.apply(compute_monthly_waste, axis=1)
    matches = apply_waste_coefficient_clipping(matches, waste_coeff)
    matches = placeholder_process_metadata_for_scoring(matches, process_metadata)

    resource_use_df = load_resource_use_template()
    emission_factors = load_resource_emission_template()
    matches = join_capacity_and_resource_use(matches, process_capacity, resource_use_df)
    matches = attach_resource_co2_column(matches, emission_factors)

    matches["transport_mode"] = matches.apply(normalize_lca_transport_mode, axis=1)

    matches["tech_score"] = compute_tech_score_series(matches, processes)

    try:
        matches = run_lca_batch_for_matches(matches)
    except Exception as e:
        logger.exception("LCA batch hatası")
        return {"status": "failed", "period": period, "error": f"LCA: {e}"}

    matches = apply_literature_transport_cost(matches)

    matches = apply_lca_totals(matches)

    matches = recompute_sustainability_scores(
        matches,
        w_env=0.60,
        w_econ=0.25,
        w_tech=0.15,
        global_bounds=global_bounds,
    )

    out_matches_name = matches_lca_filename(period)
    out_matches_path = runtime / out_matches_name
    matches.to_excel(out_matches_path, index=False)

    cap_out = process_capacity[["process_id", "capacity_monthly"]]
    cap_path = runtime / process_capacity_monthly_filename(period)
    cap_out.to_excel(cap_path, index=False)

    osb_limit = float(process_capacity["capacity_monthly"].sum())
    with open(runtime / "osb_limit.txt", "w", encoding="utf-8") as f:
        f.write(f"OSB_Limit = {osb_limit};")

    df_raw = pd.read_excel(out_matches_path)
    df_clean, clean_report = clean_matches(df_raw)
    df_excel_out = df_clean.copy()
    for _ffc in ("source_factory", "target_factory"):
        if _ffc in df_excel_out.columns:
            df_excel_out[_ffc] = df_excel_out[_ffc].map(
                lambda x: format_factory_id(x) if parse_factory_id(x) is not None else x
            )
    df_excel_out.to_excel(out_matches_path, index=False)

    milp_report: Optional[dict[str, Any]] = None
    try:
        from optimization.pulp_symbiosis import solve_symbiosis_milp

        milp_report = solve_symbiosis_milp(
            df_clean,
            cap_out,
            osb_limit,
            selected_csv=runtime / SELECTED_MATCHES_CSV,
        )
    except ImportError as e:
        return {
            "status": "failed",
            "period": period,
            "error": f"PuLP yok: pip install pulp — {e}",
            "matches_lca_path": str(out_matches_path),
            "clean_report": clean_report,
        }
    except Exception as e:
        return {
            "status": "failed",
            "period": period,
            "error": f"MILP: {e}",
            "matches_lca_path": str(out_matches_path),
            "clean_report": clean_report,
        }

    selected_csv = runtime / SELECTED_MATCHES_CSV
    raw_path = runtime / selected_raw_filename(period)
    try:
        selected_raw = extract_selected_rows(
            out_matches_path,
            selected_csv,
            selected_raw_out=raw_path,
        )
    except Exception as e:
        return {
            "status": "failed",
            "period": period,
            "error": f"Sonuç okuma: {e}",
            "matches_lca_path": str(out_matches_path),
        }

    if not selected_raw.empty:
        selected_raw, _ = clean_optimization_results(selected_raw)

    sel_path = runtime / selected_matches_filename(period)
    selected_clean = filter_selected_matches(selected_raw, period, out_path=sel_path)

    out: dict[str, Any] = {
        "status": "success",
        "period": period,
        "triggered_by": triggered_by,
        "matches_lca_path": str(out_matches_path),
        "process_capacity_path": str(cap_path),
        "selected_matches_csv": str(selected_csv),
        "selected_matches_path": str(sel_path),
        "selected_raw_path": str(raw_path),
        "matches_processed": len(df_clean),
        "matches_selected": len(selected_clean),
        "osb_limit": osb_limit,
        "clean_report": clean_report,
        "solver": "pulp",
    }
    if milp_report is not None:
        out["milp_report"] = milp_report
    return out
