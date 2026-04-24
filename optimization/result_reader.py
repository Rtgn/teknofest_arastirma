"""
`selected_matches.csv` içinden seçilen `match_id` listesini okuma yardımcıları.
"""

from __future__ import annotations

import math
import numbers
from pathlib import Path
from typing import Any, Optional

import pandas as pd

SELECTED_MATCHES_CSV = "selected_matches.csv"


def normalize_match_id(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        if v == int(v):
            return str(int(v))
        s = str(v).rstrip("0").rstrip(".")
        return s if s else str(v)
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, numbers.Integral):
        return str(int(v))
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() in ("nan", "none"):
            return ""
        try:
            f = float(s)
            if math.isfinite(f) and f == int(f):
                return str(int(f))
        except ValueError:
            pass
        return s
    try:
        if hasattr(v, "item"):
            return normalize_match_id(v.item())
    except (ValueError, TypeError, AttributeError):
        pass
    try:
        f = float(v)
        if math.isnan(f):
            return ""
        if f == int(f):
            return str(int(f))
        return str(f)
    except (TypeError, ValueError):
        return str(v).strip()


def read_selected_match_ids(selected_csv: Path, *, threshold: float = 0.5) -> list[str]:
    """
    PuLP çözücünün yazdığı ``selected_matches.csv`` (``match_id;level``) dosyasından
    ``level >= threshold`` olan match_id'leri döndürür.
    """
    if not selected_csv.is_file():
        return []
    df = pd.read_csv(selected_csv, sep=";")
    if df.empty or "match_id" not in df.columns:
        return []
    if "level" in df.columns:
        lev = pd.to_numeric(df["level"], errors="coerce").fillna(0)
        raw = df.loc[lev >= threshold, "match_id"]
    else:
        raw = df["match_id"]
    out = {normalize_match_id(x) for x in raw}
    out.discard("")
    return sorted(out)


def extract_selected_rows(
    matches_excel_path: Path,
    selected_csv: Path,
    *,
    selected_raw_out: Optional[Path] = None,
) -> pd.DataFrame:
    """
    ``selected_matches.csv`` içindeki match_id etiketlerini Excel satırlarıyla eşler.
    Excel'de ``match_id`` sütunu varsa kullanılır; yoksa satır indeksi (eski davranış).
    """
    ids = set(read_selected_match_ids(selected_csv))
    df = pd.read_csv(matches_excel_path)
    if "match_id" in df.columns:
        key = df["match_id"].map(normalize_match_id)
    else:
        key = pd.Series([normalize_match_id(i) for i in df.index], index=df.index)
    sel = df.loc[key.isin(ids)].copy()
    if selected_raw_out is not None:
        selected_raw_out.parent.mkdir(parents=True, exist_ok=True)
        sel.to_csv(selected_raw_out, index=False)
    return sel
