"""
Eşleşme satırları için türetilmiş skorlar ve ekonomik kabuller.

- **tech_score:** Proses (isteğe bağlı), geri kazanım oranı ve mesafeye dayalı 0–1 skor.
- **transport_cost:** Yol nakliyesi için literatürle uyumlu sabit €/ton·km ile ton-km maliyeti
  (Eurostat tipi yüksek seviye aralığın ortası; birim raporlama ile uyumludur).
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Yol nakliyesi: AB içi tipik aralık ~0.05–0.12 €/ton·km (yük tipi / bölgeye göre değişir).
LITERATURE_TRANSPORT_COST_EUR_PER_TON_KM = 0.07

# Teknik uygunluk: mesafe cezası ölçeği (km); ~bu değerde mesafe faktörü ~0.5 ağırlıkta
TECH_SCORE_DISTANCE_REFERENCE_KM = 50.0

# Ağırlıklar: proses bilgisi > geri kazanım > lojistik yakınlık
W_PROCESS = 0.40
W_RECOVERY = 0.35
W_DISTANCE = 0.25


def _merge_process_tech(matches: pd.DataFrame, processes: Optional[pd.DataFrame]) -> pd.Series:
    """processes.tech_score varsa process_id ile birleştirilir; yoksa 0.5."""
    n = len(matches)
    base = pd.Series(np.full(n, 0.5), index=matches.index, dtype=float)
    if processes is None or processes.empty:
        return base
    if "process_id" not in processes.columns or "tech_score" not in processes.columns:
        return base
    p = processes.drop_duplicates(subset=["process_id"], keep="last")[
        ["process_id", "tech_score"]
    ].copy()
    p["process_id"] = p["process_id"].astype(str).str.strip()
    m = matches[["process_id"]].copy()
    m["process_id"] = m["process_id"].astype(str).str.strip()
    j = m.merge(p, on="process_id", how="left")
    ts = pd.to_numeric(j["tech_score"], errors="coerce")
    return ts.fillna(0.5).clip(0.0, 1.0)


def _recovery_component(matches: pd.DataFrame) -> pd.Series:
    """waste_coefficients.recovery_rate birleşmişse kullanılır."""
    if "recovery_rate" not in matches.columns:
        return pd.Series(np.full(len(matches), 0.5), index=matches.index, dtype=float)
    r = pd.to_numeric(matches["recovery_rate"], errors="coerce").fillna(0.5)
    return r.clip(0.0, 1.0)


def _distance_factor(matches: pd.DataFrame) -> pd.Series:
    """Kısa mesafe = daha yüksek teknik uygulanabilirlik (lojistik kısıt)."""
    d = pd.to_numeric(matches["distance_km"], errors="coerce").fillna(0.1).clip(lower=0.1)
    return 1.0 / (1.0 + d / TECH_SCORE_DISTANCE_REFERENCE_KM)


def compute_tech_score_series(
    matches: pd.DataFrame,
    processes: Optional[pd.DataFrame] = None,
) -> pd.Series:
    """
    0–1 teknik skor: ``processes.tech_score`` (varsa), ``recovery_rate`` (waste_coefficients),
    ve normalize mesafe faktörünün ağırlıklı ortalaması.
    """
    if matches.empty:
        return pd.Series(dtype=float)
    proc = _merge_process_tech(matches, processes)
    rec = _recovery_component(matches)
    dist = _distance_factor(matches)
    out = W_PROCESS * proc + W_RECOVERY * rec + W_DISTANCE * dist
    out = out.clip(0.0, 1.0)
    logger.info(
        "tech_score türetildi: min=%.3f max=%.3f mean=%.3f",
        float(out.min()),
        float(out.max()),
        float(out.mean()),
    )
    return out


def apply_literature_transport_cost(
    matches: pd.DataFrame,
    *,
    eur_per_ton_km: float = LITERATURE_TRANSPORT_COST_EUR_PER_TON_KM,
) -> pd.DataFrame:
    """
    ``transport_cost = (waste_amount_monthly / 1000) * distance_km * rate``

    *waste_amount_monthly* kg/ay, *distance_km* km → ton·km × €/ton·km. Sonuç aynı ekonomik
    birim ölçeğinde (LCA ``profit`` ile tutarlı raporlama için sabit çarpan kullanın).
    """
    out = matches.copy()
    if "waste_amount_monthly" not in out.columns or "distance_km" not in out.columns:
        logger.warning("literatür transport_cost: waste_amount_monthly veya distance_km yok")
        return out
    w = pd.to_numeric(out["waste_amount_monthly"], errors="coerce").fillna(0.0).clip(lower=0.0)
    d = pd.to_numeric(out["distance_km"], errors="coerce").fillna(0.1).clip(lower=0.1)
    ton = w / 1000.0
    out["transport_cost"] = ton * d * float(eur_per_ton_km)
    return out
