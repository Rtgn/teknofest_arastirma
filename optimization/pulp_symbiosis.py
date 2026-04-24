

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from optimization.result_reader import normalize_match_id

logger = logging.getLogger(__name__)

BIG_CAP_THRESHOLD = 1e11
W_ENV_DEFAULT = 0.6
W_SCORE_DEFAULT = 0.4


def _pulp_time_limit_sec() -> Optional[int]:
    raw = os.environ.get("SYMBIOSIS_PULP_TIME_LIMIT_SEC", "").strip()
    if not raw:
        return None
    try:
        v = int(raw)
        return v if v > 0 else None
    except ValueError:
        return None


def _pick_pulp_solver():
    import pulp

    tl = _pulp_time_limit_sec()
    kwargs: dict[str, Any] = {"msg": False}
    if tl is not None:
        kwargs["timeLimit"] = tl
    return pulp.PULP_CBC_CMD(**kwargs), "CBC"


def solve_symbiosis_milp(
    matches_df: pd.DataFrame,
    capacity_df: pd.DataFrame,
    osb_limit: float,
    *,
    selected_csv: Path,
    w_env: float = W_ENV_DEFAULT,
    w_score: float = W_SCORE_DEFAULT,
) -> dict[str, Any]:

    import pulp

    df = matches_df.copy()
    if df.empty:
        selected_csv.parent.mkdir(parents=True, exist_ok=True)
        selected_csv.write_text("match_id;level\n", encoding="utf-8")
        return {"status": "empty", "objective": None, "solver": None, "n_vars": 0}

    if "match_id" not in df.columns:
        df["match_id"] = [normalize_match_id(i) for i in df.index]

    df["match_id"] = df["match_id"].map(normalize_match_id)
    df = df[df["match_id"] != ""]

    env_col = "env_score" if "env_score" in df.columns else "sustainability_score"
    if env_col not in df.columns:
        raise ValueError(f"MILP için '{env_col}' veya sustainability_score gerekli")
    for c in ("sustainability_score", "waste_amount_monthly", "waste_id", "process_id"):
        if c not in df.columns:
            raise ValueError(f"MILP için matches sütunu gerekli: {c}")

    one = df.drop_duplicates(subset=["match_id"], keep="last")
    mid_list = one["match_id"].tolist()

    S_map = dict(zip(one["match_id"], pd.to_numeric(one["sustainability_score"], errors="coerce").fillna(0.0)))
    E_map = dict(zip(one["match_id"], pd.to_numeric(one[env_col], errors="coerce").fillna(0.0)))
    W_map = dict(
        zip(one["match_id"], pd.to_numeric(one["waste_amount_monthly"], errors="coerce").fillna(0.0))
    )

    # gdx_builder._write_gams_csv_inputs ile aynı: eşleşmede görünen her j için Cap yoksa BIG_CAP
    cap_df = capacity_df.copy().assign(process_id=capacity_df["process_id"].astype(str))
    cap_map_base = dict(
        zip(cap_df["process_id"], pd.to_numeric(cap_df["capacity_monthly"], errors="coerce"))
    )
    j_list = df["process_id"].astype(str).unique().tolist()
    BIG_CAP = 1e12
    cap_map: dict[str, float] = {}
    for j_el in j_list:
        v = cap_map_base.get(j_el)
        cap_map[j_el] = float(v) if v is not None and pd.notna(v) else BIG_CAP

    prob = pulp.LpProblem("symbiosis", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("x", mid_list, cat=pulp.LpBinary)

    prob += pulp.lpSum((w_env * E_map[m] + w_score * S_map[m]) * x[m] for m in mid_list)

    # Atık başına en fazla bir seçili eşleşme
    wpairs = df[["match_id", "waste_id"]].copy()
    wpairs["match_id"] = wpairs["match_id"].map(normalize_match_id)
    wpairs["waste_id"] = wpairs["waste_id"].astype(str)
    wpairs = wpairs.drop_duplicates()
    for w_id, sub in wpairs.groupby("waste_id"):
        ms = [normalize_match_id(m) for m in sub["match_id"].unique() if str(m).strip()]
        ms = [m for m in ms if m in x]
        if len(ms) > 1:
            prob += pulp.lpSum(x[m] for m in ms) <= 1

    # Proses başına en fazla bir seçili eşleşme (her hedef proses en bir atık kabul eder)
    ppairs = df[["match_id", "process_id"]].copy()
    ppairs["match_id"] = ppairs["match_id"].map(normalize_match_id)
    ppairs["_pj"] = ppairs["process_id"].astype(str).str.strip()
    ppairs = ppairs.drop_duplicates()
    for _, sub in ppairs.groupby("_pj"):
        ms = [normalize_match_id(m) for m in sub["match_id"].unique() if str(m).strip()]
        ms = [m for m in ms if m in x]
        if len(ms) > 1:
            prob += pulp.lpSum(x[m] for m in ms) <= 1

    # OSB toplam kütle
    prob += pulp.lpSum(W_map[m] * x[m] for m in mid_list) <= float(osb_limit)

    # Proses kapasitesi (çok büyük Cap → kısıt ekleme; GAMS'taki BIG_CAP ile aynı mantık)
    df_j = df.assign(_pj=df["process_id"].astype(str))
    for j, sub in df_j.groupby("_pj"):
        j = str(j).strip()
        ms = [normalize_match_id(m) for m in sub["match_id"].unique()]
        ms = [m for m in ms if m in x]
        if not ms:
            continue
        cap_j = float(cap_map.get(j, 1e12))
        if cap_j >= BIG_CAP_THRESHOLD:
            continue
        if cap_j <= 0:
            continue
        prob += pulp.lpSum(W_map[m] * x[m] for m in ms) <= cap_j

    solver, solver_name = _pick_pulp_solver()
    prob.solve(solver)

    status_str = pulp.LpStatus.get(prob.status, str(prob.status))
    obj = pulp.value(prob.objective)

    if prob.status != pulp.LpStatusOptimal:
        raise RuntimeError(
            f"MILP optimal çözüm yok: status={status_str} ({prob.status}). "
            "Model uygunsuz olabilir veya süre sınırına takılmış olabilir (SYMBIOSIS_PULP_TIME_LIMIT_SEC)."
        )

    selected_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(selected_csv, "w", encoding="utf-8", newline="") as f:
        f.write("match_id;level\n")
        for m in mid_list:
            v = x[m].value()
            if v is None:
                v = 0.0
            f.write(f"{m};{float(v):.10g}\n")

    logger.info(
        "PuLP MILP: solver=%s, objective=%s, binaries=%s, selected=%s",
        solver_name,
        obj,
        len(mid_list),
        sum(1 for m in mid_list if (x[m].value() or 0) >= 0.5),
    )

    return {
        "status": "optimal",
        "objective": float(obj) if obj is not None else None,
        "solver": solver_name,
        "n_vars": len(mid_list),
        "lp_status": status_str,
    }

