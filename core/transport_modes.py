"""Taşıma modu: waste_process_links / physical_state → LCA batch string."""

from __future__ import annotations

import pandas as pd


def normalize_lca_transport_mode(row: pd.Series) -> str:
    """
    Önce satırdaki transport_mode (tanker/truck/pipeline), yoksa physical_state.
    LCA yükü: truck_tanker | transport_truck | pipeline
    """
    if "transport_mode" in row.index:
        tm = row.get("transport_mode")
        if tm is not None and not (isinstance(tm, float) and pd.isna(tm)) and str(tm).strip():
            m = str(tm).strip().lower()
            if m in ("tanker", "truck_tanker"):
                return "truck_tanker"
            if m == "pipeline":
                return "pipeline"
            if m in ("truck", "transport_truck"):
                return "transport_truck"
    ps = str(row.get("physical_state", "")).lower()
    if "liquid" in ps or "sıvı" in ps or "sivi" in ps:
        return "truck_tanker"
    if "gas" in ps or "gaz" in ps:
        return "pipeline"
    return "transport_truck"
