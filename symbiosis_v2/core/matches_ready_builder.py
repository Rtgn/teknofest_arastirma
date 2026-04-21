"""
factories + processes + waste_streams + waste_process_links → matches_LCA_ready.xlsx

Eski projeden kopyalanmış eşleşme dosyası yerine, güncel OSB verisiyle üretim.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.config import allow_self_symbiosis

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0

SYMBIOSIS_BUNDLE_FILES = (
    "factories.xlsx",
    "processes.xlsx",
    "waste_streams.xlsx",
    "waste_process_links.xlsx",
)


def symbiosis_bundle_complete(runtime: Path) -> bool:
    return all((runtime / f).is_file() for f in SYMBIOSIS_BUNDLE_FILES)


def _read_excel(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    try:
        return pd.read_excel(path, engine="openpyxl")
    except Exception:
        return pd.read_excel(path)


def _as_str_id(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlon1 = math.radians(lat1), math.radians(lon1)
    rlat2, rlon2 = math.radians(lat2), math.radians(lon2)
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_KM * c


_haversine_km = haversine_km  # geriye dönük iç kullanım


def _is_auxiliary(val: Any) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "evet"):
        return True
    try:
        return float(s) != 0.0
    except ValueError:
        return False


def _build_matches_from_full_links(runtime: Path, links: pd.DataFrame) -> pd.DataFrame:
    """waste_process_links_generator çıktısı: mesafe/taşıma önceden dolu."""
    if links.empty:
        raise ValueError("waste_process_links.xlsx boş.")
    processes = _read_excel(runtime / "processes.xlsx")
    proc = processes.copy()
    proc["process_id"] = proc["process_id"].map(_as_str_id)
    proc = proc[proc["process_id"] != ""].drop_duplicates(subset=["process_id"], keep="last")
    aux_col = "is_auxiliary_process" if "is_auxiliary_process" in proc.columns else None
    proc_index = proc.set_index("process_id", drop=False)

    rows_out: list[dict[str, Any]] = []
    for _, row in links.iterrows():
        tid = _as_str_id(row.get("target_process_id"))
        if not tid:
            continue
        if tid not in proc_index.index:
            raise ValueError(f"Hedef proses bulunamıyor: {tid!r}")
        if aux_col and _is_auxiliary(proc_index.loc[tid].get(aux_col)):
            logger.warning("Hedef yardımcı proses, satır atlandı: %s", tid)
            continue

        sf = int(pd.to_numeric(row["source_factory_id"], errors="coerce"))
        tf = int(pd.to_numeric(row["target_factory_id"], errors="coerce"))
        if not allow_self_symbiosis() and sf == tf:
            continue

        dist = float(pd.to_numeric(row.get("distance_km"), errors="coerce") or 0.0)
        base = float(pd.to_numeric(row.get("waste_amount_base"), errors="coerce") or 0.0)
        mid = row.get("match_id")
        rec: dict[str, Any] = {
            "waste_id": _as_str_id(row["waste_id"]),
            "process_id": tid,
            "source_factory": sf,
            "target_factory": tf,
            "waste_amount_base": base,
            "distance_km": round(dist, 4),
        }
        tm = row.get("transport_mode")
        if tm is not None and str(tm).strip():
            rec["transport_mode"] = str(tm).strip()
        if mid is not None and not (isinstance(mid, float) and pd.isna(mid)):
            try:
                rec["match_id"] = int(mid)
            except (TypeError, ValueError):
                rec["match_id"] = str(mid).strip()
        if "tech_score" in links.columns:
            ts = row.get("tech_score")
            if ts is not None and not (isinstance(ts, float) and pd.isna(ts)):
                rec["tech_score"] = float(pd.to_numeric(ts, errors="coerce") or 0.0)
        rows_out.append(rec)

    if not rows_out:
        raise ValueError("Tam şema waste_process_links sonrası geçerli satır yok")
    return pd.DataFrame(rows_out)


def build_matches_lca_ready_dataframe(runtime: Path) -> pd.DataFrame:
    """
    waste_process_links: geniş şema (generator) veya eski minimal şema (target_process_id + waste_amount_base).
    """
    links = _read_excel(runtime / "waste_process_links.xlsx")

    if (
        "source_factory_id" in links.columns
        and "target_factory_id" in links.columns
        and "target_process_id" in links.columns
        and "distance_km" in links.columns
    ):
        return _build_matches_from_full_links(runtime, links)

    factories = _read_excel(runtime / "factories.xlsx")
    processes = _read_excel(runtime / "processes.xlsx")
    waste_streams = _read_excel(runtime / "waste_streams.xlsx")

    for col in ("id", "lat", "lng"):
        if col not in factories.columns:
            raise ValueError(f"factories.xlsx içinde '{col}' kolonu gerekli")
    for col in ("process_id", "factory_id"):
        if col not in processes.columns:
            raise ValueError(f"processes.xlsx içinde '{col}' kolonu gerekli")
    for col in ("waste_id", "process_id"):
        if col not in waste_streams.columns:
            raise ValueError(f"waste_streams.xlsx içinde '{col}' kolonu gerekli (üretici proses: process_id)")

    tgt_col = "target_process_id" if "target_process_id" in links.columns else None
    if tgt_col is None and "process_id" in links.columns:
        tgt_col = "process_id"
    if tgt_col is None:
        raise ValueError(
            "waste_process_links.xlsx içinde hedef proses kolonu gerekli: "
            "'target_process_id' veya 'process_id'"
        )
    if "waste_id" not in links.columns:
        raise ValueError("waste_process_links.xlsx içinde 'waste_id' gerekli")
    if "waste_amount_base" not in links.columns:
        raise ValueError("waste_process_links.xlsx içinde 'waste_amount_base' (kg/ay) gerekli")

    fac_map = factories.set_index(factories["id"].astype(int))[
        ["lat", "lng"]
    ].apply(pd.to_numeric, errors="coerce")

    proc = processes.copy()
    proc["process_id"] = proc["process_id"].map(_as_str_id)
    proc["factory_id"] = pd.to_numeric(proc["factory_id"], errors="coerce")
    proc = proc[proc["process_id"] != ""].drop_duplicates(subset=["process_id"], keep="last")
    aux_col = "is_auxiliary_process" if "is_auxiliary_process" in proc.columns else None

    proc_index = proc.set_index("process_id", drop=False)

    ws = waste_streams.copy()
    ws["waste_id"] = ws["waste_id"].map(_as_str_id)
    ws["producer_process_id"] = ws["process_id"].map(_as_str_id)

    ws_p = ws.merge(
        proc[["process_id", "factory_id"]].rename(
            columns={"process_id": "producer_process_id", "factory_id": "source_factory"}
        ),
        on="producer_process_id",
        how="left",
    )

    waste_to_source = ws_p.drop_duplicates(subset=["waste_id"], keep="last")
    if waste_to_source["source_factory"].isna().any():
        bad = waste_to_source.loc[waste_to_source["source_factory"].isna(), "waste_id"].tolist()
        raise ValueError(
            f"Atık üretici proses processes.xlsx ile eşleşmiyor (waste_id): {bad[:10]}"
        )

    links = links.copy()
    links["waste_id"] = links["waste_id"].map(_as_str_id)
    links["target_process_id"] = links[tgt_col].map(_as_str_id)

    merged = links.merge(
        waste_to_source[["waste_id", "source_factory"]],
        on="waste_id",
        how="left",
    )

    if merged.empty:
        raise ValueError("waste_process_links ile waste_streams birleşiminden satır çıkmadı.")

    rows_out: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        tid = _as_str_id(row.get("target_process_id"))
        if not tid or tid not in proc_index.index:
            raise ValueError(f"Hedef proses bulunam veya geçersiz: {tid!r}")
        if aux_col and _is_auxiliary(proc_index.loc[tid].get(aux_col)):
            logger.warning("Hedef proses yardımcı olarak işaretli, satır atlandı: %s", tid)
            continue

        tgt_f = proc_index.loc[tid, "factory_id"]
        if pd.isna(tgt_f):
            raise ValueError(f"Hedef proses fabrika atanmamış: {tid}")
        tgt_f = int(tgt_f)
        src_f = row["source_factory"]
        if pd.isna(src_f):
            raise ValueError(f"Kaynak fabrika yok (waste_id={row.get('waste_id')})")
        src_f = int(src_f)

        if not allow_self_symbiosis() and src_f == tgt_f:
            continue

        try:
            la1, lo1 = float(fac_map.loc[src_f, "lat"]), float(fac_map.loc[src_f, "lng"])
            la2, lo2 = float(fac_map.loc[tgt_f, "lat"]), float(fac_map.loc[tgt_f, "lng"])
        except KeyError as e:
            raise ValueError(f"Fabrika koordinatı veya id eksik: {e}") from e

        dist = haversine_km(la1, lo1, la2, lo2)
        base = float(pd.to_numeric(row.get("waste_amount_base"), errors="coerce") or 0.0)

        rec: dict[str, Any] = {
            "waste_id": _as_str_id(row["waste_id"]),
            "process_id": tid,
            "source_factory": src_f,
            "target_factory": tgt_f,
            "waste_amount_base": base,
            "distance_km": round(dist, 4),
        }
        if "tech_score" in merged.columns:
            ts = row.get("tech_score")
            if ts is not None and not (isinstance(ts, float) and pd.isna(ts)):
                rec["tech_score"] = float(pd.to_numeric(ts, errors="coerce") or 0.0)
        if "match_id" in merged.columns:
            mid = row.get("match_id")
            if mid is not None and str(mid).strip():
                rec["match_id"] = str(mid).strip()

        rows_out.append(rec)

    if not rows_out:
        raise ValueError("waste_process_links sonunda geçerli eşleşme satırı kalmadı (yardımcı filtre?)")

    return pd.DataFrame(rows_out)


def write_matches_lca_ready(runtime: Path, df: Optional[pd.DataFrame] = None) -> Path:
    runtime.mkdir(parents=True, exist_ok=True)
    out = runtime / "matches_LCA_ready.xlsx"
    data = df if df is not None else build_matches_lca_ready_dataframe(runtime)
    data.to_excel(out, index=False)
    logger.info("matches_LCA_ready üretildi: %s (%s satır)", out, len(data))
    return out


def ensure_matches_lca_ready(
    runtime: Path,
    *,
    strict_symbiosis_only: bool = False,
) -> Optional[str]:
    """
    Symbiosis dörtlemesi tamamsa matches_LCA_ready.xlsx dosyasını yeniden yazar.

    strict_symbiosis_only=True: yalnızca symbiosis girdisiyle üretim; dosya eksikse hata.
    strict_symbiosis_only=False: dörtleme varsa üret; yoksa mevcut matches_LCA_ready.xlsx
    varsa dokunma; ikisi de yoksa hata mesajı döner.
    """
    runtime = Path(runtime)

    if symbiosis_bundle_complete(runtime):
        try:
            write_matches_lca_ready(runtime)
        except Exception as e:
            return f"matches_LCA_ready üretilemedi: {e}"
        return None

    if strict_symbiosis_only:
        return (
            "strict_symbiosis_only: factories.xlsx, processes.xlsx, waste_streams.xlsx, "
            "waste_process_links.xlsx dosyalarının hepsi data_runtime içinde olmalı."
        )

    if (runtime / "matches_LCA_ready.xlsx").is_file():
        logger.info("Symbiosis dörtlemesi yok; mevcut matches_LCA_ready.xlsx kullanılıyor.")
        return None

    return (
        "matches_LCA_ready.xlsx yok. Ya dosyayı el ile koyun ya da şu dört dosyayı data_runtime/ "
        f"altına ekleyin (otomatik üretim): {', '.join(SYMBIOSIS_BUNDLE_FILES)}"
    )
