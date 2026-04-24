"""
LCA mikroservisine HTTP batch istekleri; USE_MOCK_LCA=1 ile deterministik mock.
"""

from __future__ import annotations

import math
import os
from typing import Any, Optional

import pandas as pd

from core.config import ENV_USE_MOCK_LCA, get_lca_api_url, use_mock_lca
from core.transport_modes import normalize_lca_transport_mode

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


def _normalize_match_id_for_batch(v: Any, idx: Any) -> str:
    if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip():
        return str(v).strip()
    return str(idx)


def _row_float(row: pd.Series, col: str, default: float = 0.0) -> float:
    if col not in row.index:
        return default
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def run_lca_batch_for_matches(
    matches: pd.DataFrame,
    *,
    base_url: Optional[str] = None,
) -> pd.DataFrame:
    """
    POST {base_url}/calculate_lca/batch — sonuçları satırlara yazar.
    Mock: transport_co2, net_co2e, profit vb. basit değerler.
    """
    if use_mock_lca() or os.environ.get(ENV_USE_MOCK_LCA, "").lower() in ("1", "true", "yes"):
        return run_lca_batch_for_matches_mock(matches)

    if requests is None:
        raise ImportError("HTTP LCA için 'requests' paketi gerekli: pip install requests")

    url = (base_url or get_lca_api_url()).rstrip("/") + "/calculate_lca/batch"
    matches = matches.copy()
    batch_payload = []
    norm_keys_ordered: list[str] = []

    for idx, row in matches.iterrows():
        dist = float(row["distance_km"]) if "distance_km" in row.index and pd.notna(row.get("distance_km")) else 0.0
        if dist <= 0 or (isinstance(dist, float) and math.isnan(dist)):
            dist = 0.1
        amt = float(row["waste_amount_monthly"]) if "waste_amount_monthly" in row.index else 0.0
        if pd.isna(amt):
            amt = 0.0
        mid_key = _normalize_match_id_for_batch(row.get("match_id") if "match_id" in row.index else None, idx)
        norm_keys_ordered.append(mid_key)
        mode = normalize_lca_transport_mode(row)
        batch_payload.append(
            {
                "match_id": mid_key,
                "process_id": str(row["process_id"]),
                "waste_id": str(row["waste_id"]),
                "waste_amount_kg": amt,
                "distance_km": dist,
                "transport_mode": mode,
                "electricity_kwh": _row_float(row, "electricity_kwh", 0.0),
                "thermal_energy_kwh": _row_float(row, "thermal_energy_kwh", 0.0),
                "water_m3": _row_float(row, "water_m3", 0.0),
                "chemicals_kg": _row_float(row, "chemicals_kg", 0.0),
            }
        )

    r = requests.post(url, json={"matches": batch_payload}, timeout=600)
    r.raise_for_status()
    lca_results = r.json().get("results", {})

    matches["match_id"] = norm_keys_ordered

    def _g(mid: str, key: str, default: float = 0.0) -> float:
        block = lca_results.get(mid) or lca_results.get(str(mid), {})
        if not isinstance(block, dict):
            return default
        return float(block.get(key, default))

    matches["recovered_mass_monthly"] = matches["match_id"].apply(
        lambda x: _g(str(x), "recovered_mass_monthly", 0.0)
    )
    matches["transport_emissions"] = matches["match_id"].apply(lambda x: _g(str(x), "transport_co2", 0.0))
    matches["processing_emissions"] = matches["match_id"].apply(lambda x: _g(str(x), "processing_co2", 0.0))
    matches["avoided_emissions"] = matches["match_id"].apply(lambda x: _g(str(x), "avoided_co2", 0.0))
    matches["net_co2e"] = matches["match_id"].apply(lambda x: _g(str(x), "net_co2e", 0.0))
    matches["profit"] = matches["match_id"].apply(lambda x: _g(str(x), "profit", 0.0))
    matches["transport_cost"] = matches["match_id"].apply(lambda x: _g(str(x), "transport_cost", 0.0))
    return matches


def run_lca_batch_for_matches_mock(matches: pd.DataFrame) -> pd.DataFrame:
    """Servis yokken test için basit LCA benzeri sütunlar."""
    out = matches.copy()
    for col in ("electricity_kwh", "thermal_energy_kwh", "water_m3", "chemicals_kg"):
        if col not in out.columns:
            out[col] = 0.0
    mids: list[str] = []
    for i, row in out.iterrows():
        amt = float(row.get("waste_amount_monthly", 0) or 0)
        dist = float(row.get("distance_km", 0.1) or 0.1)
        if dist <= 0:
            dist = 0.1
        ton = amt / 1000.0
        out.at[i, "transport_emissions"] = round(ton * dist * 0.089 / 1000.0, 6)
        out.at[i, "processing_emissions"] = round(ton * 0.01, 6)
        out.at[i, "avoided_emissions"] = round(ton * 0.5, 6)
        out.at[i, "net_co2e"] = round(ton * 0.2, 6)
        out.at[i, "profit"] = round(ton * 10.0, 2)
        out.at[i, "transport_cost"] = round(ton * dist * 0.1, 2)
        out.at[i, "recovered_mass_monthly"] = amt * 0.8
        for col in ("electricity_kwh", "thermal_energy_kwh", "water_m3", "chemicals_kg"):
            out.at[i, col] = _row_float(row, col, 0.0)
        mid = row.get("match_id")
        mids.append(str(mid).strip() if mid is not None and str(mid).strip() else str(i))
    out["match_id"] = mids
    return out
