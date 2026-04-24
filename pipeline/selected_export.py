"""Seçilen eşleşmeler için sütun alt kümesi → Excel."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from core.config import allow_self_symbiosis
from core.factory_ids import format_factory_id, parse_factory_id
from core.period import selected_matches_filename


def filter_selected_matches(
    selected_raw: pd.DataFrame,
    period: str,
    out_path: Optional[Path] = None,
) -> pd.DataFrame:
    keep_cols = [
        "match_id",
        "waste_id",
        "process_id",
        "source_factory",
        "target_factory",
        "waste_amount_monthly",
        "recovered_mass_monthly",
        "distance_km",
        "transport_mode",
        "transport_emissions",
        "transport_cost",
        "process_resource_use",
        "processing_emissions",
        "process_cost",
        "avoided_emissions",
        "net_co2e",
        "electricity_kwh",
        "thermal_energy_kwh",
        "water_m3",
        "chemicals_kg",
        "resource_CO2",
        "process_LCA_CO2",
        "total_CO2",
        "env_score",
        "revenue",
        "avoided_disposal_cost",
        "profit",
        "economic_score",
        "tech_score",
        "sustainability_score",
    ]
    keep_cols = [c for c in keep_cols if c in selected_raw.columns]
    selected_clean = selected_raw[keep_cols].copy()
    if not allow_self_symbiosis() and "source_factory" in selected_clean.columns and "target_factory" in selected_clean.columns:
        _sf = selected_clean["source_factory"].map(parse_factory_id)
        _tf = selected_clean["target_factory"].map(parse_factory_id)
        _mask = ~(_sf.notna() & _tf.notna() & (_sf == _tf))
        selected_clean = selected_clean.loc[_mask].copy()
    for fc in ("source_factory", "target_factory"):
        if fc in selected_clean.columns:
            selected_clean[fc] = selected_clean[fc].map(
                lambda x: format_factory_id(x) if parse_factory_id(x) is not None else x
            )
    path = out_path or (Path(".") / selected_matches_filename(period))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    selected_clean.to_excel(path, index=False)
    return selected_clean
