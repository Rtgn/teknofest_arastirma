"""
Tekrar satır birleştirme, sayısal zorlama, winsorization (v1 data_cleaner ile uyumlu).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from core.factory_ids import series_factory_to_int

logger = logging.getLogger(__name__)


def coerce_excel_numeric_series(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return s

    def _one(v: Any) -> float:
        if pd.isna(v):
            return np.nan
        if isinstance(v, (bool, np.bool_)):
            return float(int(v))
        if isinstance(v, (int, np.integer)):
            return float(v)
        if isinstance(v, (float, np.floating)):
            return float(v)
        t = str(v).strip().replace("\u00a0", " ").replace(" ", "")
        if not t or t.lower() in ("nan", "none", "-", "na"):
            return np.nan
        t = t.replace("%", "")
        if "," in t and "." in t:
            if t.rfind(",") > t.rfind("."):
                t = t.replace(".", "").replace(",", ".")
            else:
                t = t.replace(",", "")
        elif "," in t:
            last = t.split(",")[-1]
            if len(last) <= 2:
                t = t.replace(",", ".")
            else:
                t = t.replace(",", "")
        try:
            return float(t)
        except ValueError:
            return np.nan

    return s.map(_one)


def _aggregate_duplicate_match_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    keys = ["waste_id", "source_factory", "target_factory", "process_id"]
    if not all(k in df.columns for k in keys) or "waste_amount_monthly" not in df.columns:
        return df, 0
    if not df.duplicated(subset=keys, keep=False).any():
        return df, 0
    before = len(df)
    d = df.copy()
    d["waste_id"] = d["waste_id"].astype(str)
    d["source_factory"] = series_factory_to_int(d["source_factory"], fill_invalid=-1)
    d["target_factory"] = series_factory_to_int(d["target_factory"], fill_invalid=-1)
    d["process_id"] = d["process_id"].astype(str)

    agg: dict = {"waste_amount_monthly": "sum"}
    for c in (
        "electricity_kwh",
        "thermal_energy_kwh",
        "water_m3",
        "chemicals_kg",
        "resource_CO2",
        "process_LCA_CO2",
        "total_CO2",
    ):
        if c in d.columns:
            agg[c] = "sum"
    for c in ("distance_km", "transport_cost", "avoided_disposal_cost"):
        if c in d.columns:
            agg[c] = "mean"
    if "tech_score" in d.columns:
        agg["tech_score"] = "max"
    first_cols = [c for c in d.columns if c not in keys and c not in agg]
    for c in first_cols:
        agg[c] = "first"
    out = d.groupby(keys, as_index=False).agg(agg)
    return out, before - len(out)


def winsorize_series(s: pd.Series, lower_pct: float = 5.0, upper_pct: float = 95.0) -> pd.Series:
    sub = s.dropna()
    if sub.empty:
        return s
    low = float(np.percentile(sub, lower_pct))
    high = float(np.percentile(sub, upper_pct))
    return s.clip(lower=low, upper=high)


def clean_matches(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if df.empty:
        return df.copy(), {"original_rows": 0, "steps": [], "final_rows": 0, "removed": 0}
    report: dict = {"original_rows": len(df), "steps": []}
    df = df.copy()

    numeric_cols = [
        "waste_amount_monthly",
        "distance_km",
        "tech_score",
        "electricity_kwh",
        "thermal_energy_kwh",
        "water_m3",
        "chemicals_kg",
        "resource_CO2",
        "process_LCA_CO2",
        "total_CO2",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df.loc[:, col] = coerce_excel_numeric_series(df[col])
            df.loc[:, col] = pd.to_numeric(df[col], errors="coerce")

    df, n_merged = _aggregate_duplicate_match_rows(df)
    if n_merged > 0:
        report["steps"].append(
            f"Yinelenen anahtarlar birleştirildi: {n_merged} satır toplandı (waste_amount_monthly=sum)"
        )

    for col in numeric_cols:
        if col in df.columns:
            nulls = df[col].isna().sum()
            if nulls > 0:
                med = df[col].median()
                if pd.isna(med):
                    med = 0.0
                df.loc[:, col] = df[col].fillna(med)
                report["steps"].append(f"{col}: {nulls} eksik → median ile dolduruldu")

    if "waste_amount_monthly" in df.columns:
        neg = (df["waste_amount_monthly"] < 0).sum()
        df.loc[:, "waste_amount_monthly"] = df["waste_amount_monthly"].clip(lower=0)
        if neg > 0:
            report["steps"].append(f"waste_amount_monthly: {neg} negatif → 0'a çekildi")

    if "distance_km" in df.columns:
        df.loc[:, "distance_km"] = df["distance_km"].clip(lower=0.1)

    if "tech_score" in df.columns:
        df.loc[:, "tech_score"] = df["tech_score"].clip(0, 1)

    if "waste_amount_monthly" in df.columns and len(df) > 20:
        before_max = df["waste_amount_monthly"].max()
        df.loc[:, "waste_amount_monthly"] = winsorize_series(df["waste_amount_monthly"])
        after_max = df["waste_amount_monthly"].max()
        report["steps"].append(
            f"waste_amount_monthly Winsorize: max {before_max:.0f} → {after_max:.0f}"
        )

    report["final_rows"] = len(df)
    report["removed"] = report["original_rows"] - report["final_rows"]
    for step in report["steps"]:
        logger.info("[DataCleaner] %s", step)
    return df, report


def clean_optimization_results(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    report = {"original_rows": len(df), "steps": []}
    if "net_co2e" in df.columns:
        df.loc[:, "net_co2e"] = df["net_co2e"].fillna(0)
    if "profit" in df.columns:
        df.loc[:, "profit"] = df["profit"].fillna(0)
    if "sustainability_score" in df.columns:
        df.loc[:, "sustainability_score"] = df["sustainability_score"].clip(0, 1).fillna(0)
    report["final_rows"] = len(df)
    return df, report
