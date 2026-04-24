"""
Dijital ikiz: baz ay + fabrika/proses aktivite ve kapasite çarpanları → MILP yeniden çözümü.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from core.factory_ids import parse_factory_id

logger = logging.getLogger(__name__)

# Kaynak çarpanı ~0 ise o fabrikadaki proseslerin kapasitesi de sıfırlanır (processes.csv gerekir)
_FACTORY_INACTIVE_EPS = 1e-9
# MILP amacı W kullanmadığı için sıfır atıklı satırlar zorunlu elenir
_MIN_WASTE_KG_FOR_MILP = 1e-6


@dataclass
class DigitalTwinOverrides:
    """
    Fabrika aktivitesi: hem kaynak hem hedef fabrikada ``waste_amount_monthly`` çarpanı (0–1+).
    Kaynak 0 → o fabrikadan çıkan atık akışı yok; hedef 0 → o fabrikaya giren atık akışı yok.
    Hedef proses: ``process_accept_mult`` ile o prosese gelen atık miktarı; ``process_capacity_mult`` ile aylık kapasite.
    """

    factory_activity: dict[str, float] = field(default_factory=dict)
    process_capacity_mult: dict[str, float] = field(default_factory=dict)
    process_accept_mult: dict[str, float] = field(default_factory=dict)
    global_capacity_mult: float = 1.0
    global_waste_mult: float = 1.0

    @classmethod
    def from_payload(cls, d: Optional[dict[str, Any]]) -> "DigitalTwinOverrides":
        if not d:
            return cls()
        return cls(
            factory_activity={str(k): float(v) for k, v in (d.get("factory_activity") or {}).items()},
            process_capacity_mult={
                str(k).strip(): float(v) for k, v in (d.get("process_capacity_mult") or {}).items()
            },
            process_accept_mult={
                str(k).strip(): float(v) for k, v in (d.get("process_accept_mult") or {}).items()
            },
            global_capacity_mult=float(d.get("global_capacity_mult", 1.0) or 1.0),
            global_waste_mult=float(d.get("global_waste_mult", 1.0) or 1.0),
        )


def _lookup(d: dict[str, float], key: Optional[Any], default: float = 1.0) -> float:
    if key is None:
        return default
    try:
        ik = int(key)
        if str(ik) in d:
            return float(d[str(ik)])
    except (TypeError, ValueError):
        pass
    sk = str(key).strip()
    if sk in d:
        return float(d[sk])
    return default


def _zero_capacity_for_processes_at_inactive_factories(
    cap_df: pd.DataFrame,
    processes_df: pd.DataFrame,
    factory_activity: dict[str, float],
) -> pd.DataFrame:
    """Kaynak aktivitesi ~0 olan fabrikadaki tüm proseslerin aylık kapasitesini sıfırlar."""
    c = cap_df.copy()
    inactive_fac: set[int] = set()
    for k, v in factory_activity.items():
        try:
            if float(v) > _FACTORY_INACTIVE_EPS:
                continue
        except (TypeError, ValueError):
            continue
        fid = parse_factory_id(k)
        if fid is not None:
            inactive_fac.add(int(fid))
    if not inactive_fac or "process_id" not in processes_df.columns:
        return c
    fc = None
    for col in ("factory_id", "fabrika_id"):
        if col in processes_df.columns:
            fc = col
            break
    if fc is None:
        return c
    proc = processes_df.copy()
    proc["process_id"] = proc["process_id"].astype(str).str.strip()
    proc["_fac"] = proc[fc].map(parse_factory_id)
    bad_pids = set(proc.loc[proc["_fac"].isin(inactive_fac), "process_id"].astype(str).str.strip())
    if not bad_pids:
        return c
    mask = c["process_id"].astype(str).str.strip().isin(bad_pids)
    n = int(mask.sum())
    if n:
        c.loc[mask, "capacity_monthly"] = 0.0
        logger.info(
            "İnaktif fabrika(lar) için %s proses satırında kapasite sıfırlandı (processes.%s).",
            n,
            fc,
        )
    return c


def apply_digital_twin_overrides(
    matches: pd.DataFrame,
    cap_df: pd.DataFrame,
    o: DigitalTwinOverrides,
    *,
    processes_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Baz ``matches_LCA`` ve ``process_capacity_monthly`` üzerinde çarpanları uygular; kâr/CO₂ kabaca ölçeklenir."""
    m = matches.copy()
    c = cap_df.copy()

    if "waste_amount_monthly" not in m.columns:
        raise ValueError("matches içinde waste_amount_monthly gerekli")
    if "capacity_monthly" not in c.columns or "process_id" not in c.columns:
        raise ValueError("cap_df içinde process_id ve capacity_monthly gerekli")

    m["waste_amount_monthly"] = pd.to_numeric(m["waste_amount_monthly"], errors="coerce").fillna(0.0)
    old_w = m["waste_amount_monthly"].replace(0.0, np.nan)

    if "source_factory" in m.columns:
        sf = m["source_factory"].map(parse_factory_id)
        src_m = sf.map(lambda x: _lookup(o.factory_activity, x, 1.0))
    else:
        src_m = pd.Series(1.0, index=m.index)

    if "target_factory" in m.columns:
        tf = m["target_factory"].map(parse_factory_id)
        tgt_m = tf.map(lambda x: _lookup(o.factory_activity, x, 1.0))
    else:
        tgt_m = pd.Series(1.0, index=m.index)

    pid = m["process_id"].astype(str).str.strip() if "process_id" in m.columns else pd.Series("", index=m.index)
    acc_m = pid.map(lambda p: _lookup(o.process_accept_mult, p, 1.0))

    m["waste_amount_monthly"] = (
        m["waste_amount_monthly"] * src_m * tgt_m * acc_m * float(o.global_waste_mult)
    )
    m["waste_amount_monthly"] = m["waste_amount_monthly"].clip(lower=0.0)

    ratio = (m["waste_amount_monthly"] / old_w).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    ratio = ratio.clip(lower=0.0, upper=1e6)
    for col in ("profit", "net_co2e", "total_CO2"):
        if col in m.columns:
            m[col] = pd.to_numeric(m[col], errors="coerce").fillna(0.0) * ratio

    c["capacity_monthly"] = pd.to_numeric(c["capacity_monthly"], errors="coerce").fillna(0.0)
    cpid = c["process_id"].astype(str).str.strip()
    cap_m = cpid.map(lambda p: _lookup(o.process_capacity_mult, p, 1.0))
    c["capacity_monthly"] = (c["capacity_monthly"] * cap_m * float(o.global_capacity_mult)).clip(lower=0.0)

    if processes_df is not None and o.factory_activity:
        c = _zero_capacity_for_processes_at_inactive_factories(c, processes_df, o.factory_activity)

    n_m = len(m)
    m = m[m["waste_amount_monthly"] > _MIN_WASTE_KG_FOR_MILP].copy()
    if len(m) < n_m:
        logger.info(
            "MILP amacı W kullanmadığı için atığı sıfır olan %s eşleşme satırı çıkarıldı.",
            n_m - len(m),
        )

    cap_before = float(pd.to_numeric(cap_df["capacity_monthly"], errors="coerce").fillna(0).sum())
    logger.info(
        "Dijital ikiz: waste toplamı %.0f → %.0f kg; kapasite toplamı %.0f → %.0f",
        float(old_w.fillna(0).sum()),
        float(m["waste_amount_monthly"].sum()),
        cap_before,
        float(c["capacity_monthly"].sum()),
    )
    return m, c


def run_digital_twin_simulation(
    base_period: str,
    payload: Optional[dict[str, Any]],
    *,
    scenario_id: Optional[int] = None,
    runtime_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Web/API: çarpanları uygula → senaryo MILP (LCA yeniden çalışmaz)."""
    import secrets

    from pipeline.scenario import run_scenario_pipeline

    sid = scenario_id if scenario_id is not None else (secrets.randbelow(800_000) + 100_000)
    dt = DigitalTwinOverrides.from_payload(payload)
    return run_scenario_pipeline(
        sid,
        base_period,
        digital_twin=dt,
        rerun_lca=False,
        triggered_by="digital_twin",
        runtime_dir=runtime_dir,
    )
