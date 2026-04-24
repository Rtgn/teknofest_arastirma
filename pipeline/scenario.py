"""
Senaryo pipeline: baz periyot + modifikasyonlar → LCA → MILP → senaryo sonuçları.
"""

from __future__ import annotations

import logging
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pipeline.digital_twin import DigitalTwinOverrides

import pandas as pd

_V2_ROOT = Path(__file__).resolve().parent.parent
if str(_V2_ROOT) not in sys.path:
    sys.path.insert(0, str(_V2_ROOT))

from core.config import RUNTIME_DIR
from core.data_cleaning import clean_matches, clean_optimization_results
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
    process_capacity_monthly_filename,
    selected_matches_filename,
    selected_raw_filename,
    simulation_period,
)
from core.match_derived_metrics import apply_literature_transport_cost, compute_tech_score_series
from core.scoring import recompute_sustainability_scores
from optimization.result_reader import SELECTED_MATCHES_CSV, extract_selected_rows
from pipeline.monthly import placeholder_process_metadata_for_scoring
from pipeline.selected_export import filter_selected_matches

logger = logging.getLogger(__name__)


@dataclass
class ScenarioWasteBounds:
    global_min_kg_month: Optional[float] = None
    global_max_kg_month: Optional[float] = None
    per_waste_kg_min: dict[str, float] = field(default_factory=dict)
    per_waste_kg_max: dict[str, float] = field(default_factory=dict)


def apply_scenario_waste_bounds(
    matches: pd.DataFrame,
    bounds: ScenarioWasteBounds,
    *,
    waste_col: str = "waste_id",
    amount_col: str = "waste_amount_monthly",
) -> pd.DataFrame:
    df = matches.copy()
    if amount_col not in df.columns:
        return df

    def _clip_row(row: pd.Series) -> float:
        v = float(row[amount_col] or 0.0)
        wid = str(row.get(waste_col, "")).strip()
        lo = bounds.global_min_kg_month
        hi = bounds.global_max_kg_month
        if wid in bounds.per_waste_kg_min:
            lo = (
                bounds.per_waste_kg_min[wid]
                if lo is None
                else max(lo, bounds.per_waste_kg_min[wid])
            )
        if wid in bounds.per_waste_kg_max:
            hi = (
                bounds.per_waste_kg_max[wid]
                if hi is None
                else min(hi, bounds.per_waste_kg_max[wid])
            )
        if lo is not None:
            v = max(v, float(lo))
        if hi is not None:
            v = min(v, float(hi))
        return float(v)

    df[amount_col] = df.apply(_clip_row, axis=1)
    return df


def emission_limits_report(
    emission_limits: pd.DataFrame,
    *,
    scenario_id: int,
    base_period: str,
    extra_notes: Optional[str] = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if emission_limits is not None and not emission_limits.empty:
        for _, r in emission_limits.iterrows():
            rows.append(
                {
                    "process_id": r.get("process_id"),
                    "parameter": r.get("parameter"),
                    "min": r.get("min"),
                    "max": r.get("max"),
                    "unit": r.get("unit"),
                    "bref_reference": r.get("bref_reference"),
                }
            )
    return {
        "scenario_id": scenario_id,
        "base_period": base_period,
        "emission_limits_row_count": len(rows),
        "limits": rows,
        "notes": extra_notes,
    }


def run_scenario_pipeline(
    scenario_id: int,
    base_period: str,
    *,
    waste_bounds: Optional[ScenarioWasteBounds] = None,
    digital_twin: Optional["DigitalTwinOverrides"] = None,
    rerun_lca: bool = False,
    triggered_by: str = "api",
    runtime_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """
    Baz: `outputs/runtime/matches_LCA_{base_period}.xlsx` ve ayni dizinde
    `process_capacity_monthly_{base_period}.xlsx`.

    ``digital_twin``: fabrika/proses çarpanları (bkz. ``pipeline.digital_twin``) — MILP öncesi uygulanır.

    Çıktı: `simulation_period` etiketi ile dosyalar ve `emission_limits_report`.
    Başarıda ``matches_LCA_{sim_p}.xlsx`` ve ``selected_matches_{sim_p}.csv`` runtime köküne kopyalanır (ağ API).
    """
    runtime = Path(runtime_dir or RUNTIME_DIR)
    sim_p = simulation_period(base_period, scenario_id)
    work = runtime / "scenario_runs" / str(scenario_id)
    work.mkdir(parents=True, exist_ok=True)

    m_path = runtime / matches_lca_filename(base_period)
    c_path = runtime / process_capacity_monthly_filename(base_period)
    if not m_path.is_file():
        return {"status": "failed", "error": f"Baz dosya yok: {m_path}"}
    if not c_path.is_file():
        return {"status": "failed", "error": f"Kapasite dosyası yok: {c_path}"}

    emission_limits_df: Optional[pd.DataFrame] = None
    el_path = runtime / "bref_emission_limits.xlsx"
    if el_path.is_file():
        emission_limits_df = pd.read_excel(el_path)

    report_limits = emission_limits_report(
        emission_limits_df if emission_limits_df is not None else pd.DataFrame(),
        scenario_id=scenario_id,
        base_period=base_period,
    )

    matches = pd.read_excel(m_path)
    cap_df = pd.read_excel(c_path)

    proc_path = runtime / "processes.xlsx"
    if digital_twin is not None:
        from pipeline.digital_twin import apply_digital_twin_overrides

        processes_for_dt = pd.read_excel(proc_path) if proc_path.is_file() else None
        matches, cap_df = apply_digital_twin_overrides(
            matches, cap_df, digital_twin, processes_df=processes_for_dt
        )
        if matches.empty:
            return {
                "status": "failed",
                "error": "Dijital ikiz sonrası eşleşme kalmadı (tüm atık akışları sıfır veya MILP için elendi).",
                "emission_limits_report": report_limits,
            }

    processes_for_tech = pd.read_excel(proc_path) if proc_path.is_file() else None

    process_metadata_path = runtime / "process_metadata.xlsx"
    process_metadata = (
        pd.read_excel(process_metadata_path) if process_metadata_path.is_file() else None
    )

    if waste_bounds is not None:
        matches = apply_scenario_waste_bounds(matches, waste_bounds)

    matches = placeholder_process_metadata_for_scoring(matches, process_metadata)

    matches["tech_score"] = compute_tech_score_series(matches, processes_for_tech)

    resource_use_df = load_resource_use_template()
    emission_factors = load_resource_emission_template()

    if rerun_lca:
        matches = join_capacity_and_resource_use(matches, cap_df, resource_use_df)
        matches = attach_resource_co2_column(matches, emission_factors)
        try:
            matches = run_lca_batch_for_matches(matches)
        except Exception as e:
            logger.exception("Senaryo LCA hatası")
            return {"status": "failed", "error": f"LCA: {e}", "emission_limits_report": report_limits}
        matches = apply_literature_transport_cost(matches)
        matches = apply_lca_totals(matches)
    elif "total_CO2" not in matches.columns and "net_co2e" in matches.columns:
        matches = join_capacity_and_resource_use(matches, cap_df, resource_use_df)
        matches = attach_resource_co2_column(matches, emission_factors)
        matches = apply_lca_totals(matches)

    matches = recompute_sustainability_scores(matches)

    out_m = work / matches_lca_filename(sim_p)
    out_c = work / process_capacity_monthly_filename(sim_p)
    matches.to_excel(out_m, index=False)
    cap_df.to_excel(out_c, index=False)

    osb_limit = float(pd.to_numeric(cap_df["capacity_monthly"], errors="coerce").fillna(0).sum())
    with open(work / "osb_limit.txt", "w", encoding="utf-8") as f:
        f.write(f"OSB_Limit = {osb_limit};")

    df_clean, clean_report = clean_matches(matches)
    df_clean.to_excel(out_m, index=False)

    milp_report: Optional[dict[str, Any]] = None
    try:
        from optimization.pulp_symbiosis import solve_symbiosis_milp

        milp_report = solve_symbiosis_milp(
            df_clean,
            cap_df,
            osb_limit,
            selected_csv=work / SELECTED_MATCHES_CSV,
        )
    except ImportError as e:
        return {
            "status": "failed",
            "error": f"PuLP yok: pip install pulp — {e}",
            "emission_limits_report": report_limits,
            "matches_path": str(out_m),
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": f"MILP: {e}",
            "emission_limits_report": report_limits,
            "matches_path": str(out_m),
        }

    selected_csv = work / SELECTED_MATCHES_CSV
    raw_path = work / selected_raw_filename(sim_p)
    try:
        selected_raw = extract_selected_rows(out_m, selected_csv, selected_raw_out=raw_path)
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Sonuç okuma: {e}",
            "emission_limits_report": report_limits,
        }

    if not selected_raw.empty:
        selected_raw, _ = clean_optimization_results(selected_raw)

    sel_final = runtime / selected_matches_filename(sim_p)
    selected_clean = filter_selected_matches(selected_raw, sim_p, out_path=sel_final)

    try:
        dest_m = runtime / matches_lca_filename(sim_p)
        shutil.copyfile(out_m, dest_m)
        if selected_csv.is_file():
            trace_csv = runtime / f"selected_matches_{sim_p}.csv"
            shutil.copyfile(selected_csv, trace_csv)
    except OSError as exc:
        logger.warning("Senaryo çıktısı runtime köküne kopyalanamadı: %s", exc)

    out: dict[str, Any] = {
        "status": "success",
        "scenario_id": scenario_id,
        "base_period": base_period,
        "simulation_period": sim_p,
        "triggered_by": triggered_by,
        "rerun_lca": rerun_lca,
        "work_dir": str(work),
        "matches_path": str(out_m),
        "capacity_path": str(out_c),
        "matches_lca_runtime": str(runtime / matches_lca_filename(sim_p)),
        "selected_matches_csv": str(selected_csv),
        "selected_matches_path": str(sel_final),
        "matches_selected": len(selected_clean),
        "emission_limits_report": report_limits,
        "clean_report": clean_report,
        "solver": "pulp",
    }
    if milp_report is not None:
        out["milp_report"] = milp_report
    return out
