"""
`selected_matches.csv` içinden seçilen `match_id` listesini okuma yardımcıları.
"""

from __future__ import annotations

import math
import numbers
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

SELECTED_MATCHES_CSV = "selected_matches.csv"


def _recover_mangled_pc5_semicolon_lines(lines: list[str]) -> pd.DataFrame:
    """`csvout.pc=5` ile Put birlikte bozulmuş satırlardan `match_id` ve `level` çıkarır."""
    data: list[dict[str, Any]] = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        lev_m = re.search(r"([\d.]+)\s*$", line)
        if not lev_m:
            continue
        try:
            lev = float(lev_m.group(1))
        except ValueError:
            continue
        id_m = re.search(r"^[^\d]*(\d+)", line)
        if not id_m:
            continue
        data.append({"match_id": id_m.group(1), "level": lev})
    return pd.DataFrame(data)


def _read_selected_matches_table(path: Path) -> pd.DataFrame:
    """
    GAMS Put + csvout.pc=5 ile yazılan eski dosyalarda satırlar
    ``\"0\",\",\",0.0`` biçiminde **üç sütun** olabiliyor (virgül ayrı alan).
    pc=5 + ';' baska bozulma: tek satirda yuzlerce ayirici.

    Duzen cikti: pc=0, satir basina match_id;level ve 0;0.0 (duz metin).
    """
    import csv
    import io

    raw_text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = raw_text.strip().splitlines()
    if not lines:
        return pd.DataFrame(columns=["match_id", "level"])

    # Temiz ';' CSV: tam 2 sutun (pc=0 GAMS ciktisi)
    if ";" in lines[0]:
        try:
            df_try = pd.read_csv(io.StringIO(raw_text), sep=";")
            cols_ok = (
                "match_id" in df_try.columns
                and "level" in df_try.columns
                and len(df_try.columns) == 2
            )
            if cols_ok:
                return df_try
        except Exception:
            pass
        # Bozuk pc=5 + ';'
        rec = _recover_mangled_pc5_semicolon_lines(lines)
        if not rec.empty:
            return rec

    rows = list(csv.reader(lines))
    if not rows:
        return pd.DataFrame(columns=["match_id", "level"])

    # Virgülle tek başlık + veri satırı 3 alan: ['9', ',', '1.0']
    if len(rows) >= 2 and len(rows[1]) >= 3:
        r1 = rows[1]
        # GAMS hatası: ayırıcı virgül ayrı sütun olmuş
        if r1[1] == ",":
            data: list[dict[str, Any]] = []
            for row in rows[1:]:
                if len(row) < 3:
                    continue
                mid = str(row[0]).strip().strip('"').strip("'")
                try:
                    lev = float(str(row[2]).strip())
                except ValueError:
                    continue
                data.append({"match_id": mid, "level": lev})
            return pd.DataFrame(data)

    try:
        df = pd.read_csv(io.StringIO(raw_text))
        if "match_id" in df.columns and "level" in df.columns:
            return df
    except Exception:
        pass

    return pd.DataFrame(columns=["match_id", "level"])


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
    GAMS'in yazdigi selected_matches.csv (match_id, level) dosyasindan
    level >= threshold olan match_id'leri dondurur.
    """
    if not selected_csv.is_file():
        return []
    df = _read_selected_matches_table(selected_csv)
    if df.empty:
        return []
    cols = {str(c).strip().lower(): c for c in df.columns}
    mid_col = cols.get("match_id")
    if not mid_col:
        return []
    if "level" in cols:
        lev = pd.to_numeric(df[cols["level"]], errors="coerce").fillna(0)
        take = lev >= threshold
        raw = df.loc[take, mid_col]
    else:
        raw = df[mid_col]
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
    ``selected_matches.csv`` içindeki GAMS ``m`` etiketleri (match_id) ile Excel satırlarını eşler.

    GAMS ``matches.gdx`` / ``gams_S.csv`` ilk sütundaki **match_id** değerlerini kullanır; satır
    indeksi (0,1,…) ile aynı olmayabilir (ör. ``clean_matches`` birleştirmesi). Bu yüzden
    Excel'de ``match_id`` sütunu varsa o kullanılır — yoksa indeks (eski davranış).
    """
    ids = set(read_selected_match_ids(selected_csv))
    df = pd.read_excel(matches_excel_path)
    if "match_id" in df.columns:
        key = df["match_id"].map(normalize_match_id)
    else:
        key = pd.Series([normalize_match_id(i) for i in df.index], index=df.index)
    sel = df.loc[key.isin(ids)].copy()
    if selected_raw_out is not None:
        selected_raw_out.parent.mkdir(parents=True, exist_ok=True)
        sel.to_excel(selected_raw_out, index=False)
    return sel
