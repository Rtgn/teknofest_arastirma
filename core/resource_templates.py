"""
resource_use_template ve resource_emission_template yükleme; aylık kaynak ve CO₂.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.config import RESOURCE_EMISSION_TEMPLATE_PATH, RESOURCE_USE_TEMPLATE_PATH

logger = logging.getLogger(__name__)

# process_metadata'tan türetilen şablondaki sütun adları (ton ürün başına)
RESOURCE_USE_PER_TON_COLS = (
    "electricity_kwh_per_ton",
    "thermal_energy_kwh_per_ton",
    "water_m3_per_ton",
    "chemicals_kg_per_ton",
)

def read_schema_table(path: Path) -> pd.DataFrame:
    """Excel veya yanlış uzantılı CSV için esnek okuma."""
    if not path.is_file():
        return pd.DataFrame()
    for reader in (
        lambda p: pd.read_excel(p, engine="openpyxl"),
        lambda p: pd.read_excel(p),
        lambda p: pd.read_csv(p),
    ):
        try:
            return reader(path)
        except Exception:
            continue
    logger.warning("Şablon okunamadı: %s", path)
    return pd.DataFrame()


def load_resource_use_template(path: Optional[Path] = None) -> pd.DataFrame:
    p = path or RESOURCE_USE_TEMPLATE_PATH
    df = read_schema_table(p)
    if df.empty:
        logger.info("resource_use_template bulunamadı veya boş: %s", p)
        return df
    if "process_id" not in df.columns:
        logger.warning("resource_use_template içinde process_id yok: %s", p)
        return pd.DataFrame()
    df = df.copy()
    df["process_id"] = df["process_id"].astype(str).str.strip()
    return df.drop_duplicates(subset=["process_id"], keep="last")


def emission_factor_map(emission_df: pd.DataFrame) -> dict[str, float]:
    """resource_type → kg CO2 / birim (birim sütunundaki tanıma göre)."""
    if emission_df is None or emission_df.empty or "resource_type" not in emission_df.columns:
        return {}
    fac_col = "emission_factor"
    if fac_col not in emission_df.columns:
        alt = "emission_factor_kg_co2_per_unit"
        if alt in emission_df.columns:
            fac_col = alt
        else:
            return {}
    out: dict[str, float] = {}
    for _, row in emission_df.iterrows():
        key = str(row["resource_type"]).strip().lower()
        try:
            out[key] = float(row[fac_col])
        except (TypeError, ValueError):
            out[key] = 0.0
    return out


def load_resource_emission_template(path: Optional[Path] = None) -> dict[str, float]:
    p = path or RESOURCE_EMISSION_TEMPLATE_PATH
    df = read_schema_table(p)
    return emission_factor_map(df)


def _as_float_series(s: Any, default: float = 0.0) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    return x.fillna(default)


def join_capacity_and_resource_use(
    matches: pd.DataFrame,
    process_capacity: pd.DataFrame,
    resource_use: pd.DataFrame,
) -> pd.DataFrame:
    """
    process_id üzerinden aylık kapasite (kg/ay) ve ton başına şablon ile
    electricity_kwh, thermal_energy_kwh, water_m3, chemicals_kg üretir.
    """
    out = matches.copy()
    if "process_id" not in out.columns:
        for c in (
            "electricity_kwh",
            "thermal_energy_kwh",
            "water_m3",
            "chemicals_kg",
        ):
            out[c] = 0.0
        return out

    out["process_id"] = out["process_id"].astype(str).str.strip()
    cap = process_capacity
    if cap is None or cap.empty or "capacity_monthly" not in cap.columns:
        cap_part = out[["process_id"]].drop_duplicates()
        cap_part["capacity_monthly"] = 0.0
    else:
        cap_part = cap[["process_id", "capacity_monthly"]].copy()
        cap_part["process_id"] = cap_part["process_id"].astype(str).str.strip()
        cap_part = cap_part.drop_duplicates(subset=["process_id"], keep="last")

    merged = out.merge(cap_part, on="process_id", how="left")
    merged["capacity_monthly"] = _as_float_series(merged["capacity_monthly"], 0.0)

    if resource_use is None or resource_use.empty:
        ru = merged[["process_id"]].drop_duplicates()
        for col in RESOURCE_USE_PER_TON_COLS:
            ru[col] = 0.0
        merged = merged.drop(columns=[c for c in RESOURCE_USE_PER_TON_COLS if c in merged.columns], errors="ignore")
        merged = merged.merge(ru, on="process_id", how="left", suffixes=("", "_ru"))
    else:
        ru = resource_use.copy()
        for col in RESOURCE_USE_PER_TON_COLS:
            if col not in ru.columns:
                ru[col] = 0.0
        ru = ru[["process_id"] + list(RESOURCE_USE_PER_TON_COLS)]
        merged = merged.drop(columns=[c for c in RESOURCE_USE_PER_TON_COLS if c in merged.columns], errors="ignore")
        merged = merged.merge(ru, on="process_id", how="left", suffixes=("", "_ru"))

    for col in RESOURCE_USE_PER_TON_COLS:
        merged[col] = _as_float_series(merged[col], 0.0)

    # Kapasite kg/ay → ton/ay; şablon ton başına
    ton_monthly = merged["capacity_monthly"] / 1000.0
    merged["electricity_kwh"] = ton_monthly * merged["electricity_kwh_per_ton"]
    merged["thermal_energy_kwh"] = ton_monthly * merged["thermal_energy_kwh_per_ton"]
    merged["water_m3"] = ton_monthly * merged["water_m3_per_ton"]
    merged["chemicals_kg"] = ton_monthly * merged["chemicals_kg_per_ton"]

    drop_extra = [c for c in RESOURCE_USE_PER_TON_COLS if c in merged.columns]
    merged = merged.drop(columns=drop_extra, errors="ignore")
    return merged


def compute_resource_co2(
    df: pd.DataFrame,
    emission_factors: dict[str, float],
) -> pd.Series:
    """kg CO2 — faktör birimleri: kWh, kWh, m3, kg ile uyumlu."""
    e = {k.lower(): v for k, v in emission_factors.items()}
    fe = float(e.get("electricity", 0.0))
    ft = float(e.get("thermal_energy", 0.0))
    fw = float(e.get("water", 0.0))
    fc = float(e.get("chemicals", 0.0))
    elec = _as_float_series(df.get("electricity_kwh"), 0.0)
    the = _as_float_series(df.get("thermal_energy_kwh"), 0.0)
    wat = _as_float_series(df.get("water_m3"), 0.0)
    chm = _as_float_series(df.get("chemicals_kg"), 0.0)
    return elec * fe + the * ft + wat * fw + chm * fc


def attach_resource_co2_column(df: pd.DataFrame, emission_factors: dict[str, float]) -> pd.DataFrame:
    out = df.copy()
    out["resource_CO2"] = compute_resource_co2(out, emission_factors)
    return out


def apply_lca_totals(matches_after_lca: pd.DataFrame) -> pd.DataFrame:
    """
    LCA sonrası: process_LCA_CO2 = net_co2e; total_CO2 = process_LCA_CO2 + resource_CO2
    """
    out = matches_after_lca.copy()
    if "net_co2e" not in out.columns:
        out["net_co2e"] = 0.0
    out["process_LCA_CO2"] = pd.to_numeric(out["net_co2e"], errors="coerce").fillna(0.0)
    if "resource_CO2" not in out.columns:
        out["resource_CO2"] = 0.0
    else:
        out["resource_CO2"] = pd.to_numeric(out["resource_CO2"], errors="coerce").fillna(0.0)
    out["total_CO2"] = out["process_LCA_CO2"] + out["resource_CO2"]
    return out
