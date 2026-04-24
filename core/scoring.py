"""
LCA çıktılarından env / econ / sürdürülebilirlik skoru (v1 generate_monthly_data ile uyumlu).
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd


def recompute_sustainability_scores(
    matches: pd.DataFrame,
    *,
    w_env: float = 0.60,
    w_econ: float = 0.25,
    w_tech: float = 0.15,
    global_bounds: Optional[dict[str, float]] = None,
) -> pd.DataFrame:
    """
    net_co2e, profit, tech_score üzerinden env_score, economic_score, sustainability_score.
    """
    matches = matches.copy()
    if "net_co2e" not in matches.columns:
        matches["net_co2e"] = 0.0
    if "profit" not in matches.columns:
        matches["profit"] = 0.0
    if "tech_score" not in matches.columns:
        matches["tech_score"] = 0.5

    s = float(w_env) + float(w_econ) + float(w_tech)
    if s <= 0:
        w_env, w_econ, w_tech = 0.60, 0.25, 0.15
    else:
        w_env, w_econ, w_tech = float(w_env) / s, float(w_econ) / s, float(w_tech) / s

    if "total_CO2" in matches.columns:
        co2_for_env = pd.to_numeric(matches["total_CO2"], errors="coerce").fillna(0.0)
    else:
        co2_for_env = pd.to_numeric(matches["net_co2e"], errors="coerce").fillna(0.0)

    co2_scale = max(co2_for_env.abs().quantile(0.95), 1e-6)
    matches["env_score"] = 0.5 + (co2_for_env / (2.0 * co2_scale))
    matches["env_score"] = matches["env_score"].clip(0, 1)

    if global_bounds is not None:
        pmin = global_bounds["profit_min"]
        pmax = global_bounds["profit_max"]
    else:
        pmin, pmax = matches["profit"].min(), matches["profit"].max()

    matches["economic_score"] = (matches["profit"] - pmin) / (pmax - pmin + 1e-9)
    matches["economic_score"] = matches["economic_score"].clip(0, 1)

    matches["sustainability_score"] = (
        w_env * matches["env_score"]
        + w_econ * matches["economic_score"]
        + w_tech * matches["tech_score"]
    )
    matches["sustainability_score"] = matches["sustainability_score"].astype(float)
    return matches.fillna(0)
