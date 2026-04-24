"""
Fabrika kimlikleri: iç işlemlerde int, dışa aktarımda `f_1`, `f_2` biçimi.

Excel ve eski dosyalarda 1, "1", "f_1", "F_12" karışık gelebilir; hepsini tek sayıya indirger.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import numpy as np
import pandas as pd

_RE_F_PREFIX = re.compile(r"^[Ff]_(\d+)$")


def parse_factory_id(val: Any) -> Optional[int]:
    """Fabrika kimliğini int'e çevirir; tanınmazsa None."""
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, float):
        if not np.isfinite(val) or pd.isna(val):
            return None
        return int(val)
    s = str(val).strip().replace("\u00a0", " ")
    if not s or s.lower() in ("nan", "none", "-", "—", "#n/a"):
        return None
    s_compact = s.replace(" ", "")
    m = _RE_F_PREFIX.match(s_compact)
    if m:
        return int(m.group(1))
    try:
        return int(float(s_compact.replace(",", ".")))
    except (ValueError, TypeError):
        pass
    m2 = re.search(r"-?(\d+)", s_compact)
    if m2:
        try:
            return int(m2.group(1))
        except ValueError:
            pass
    return None


def format_factory_id(n: Any) -> str:
    """Görüntüleme için tutarlı `f_{n}` (n pozitif int beklenir)."""
    p = parse_factory_id(n)
    if p is None:
        return ""
    return f"f_{int(p)}"


def series_factory_to_int(s: pd.Series, *, fill_invalid: int = -1) -> pd.Series:
    """DataFrame sütununu fabrika int listesine çevirir (birleştirme / join için)."""
    out = s.map(lambda x: parse_factory_id(x))
    return pd.to_numeric(out, errors="coerce").fillna(fill_invalid).astype(int)


def validate_matches_against_processes_and_streams(
    matches: pd.DataFrame,
    processes: pd.DataFrame,
    waste_streams: pd.DataFrame,
) -> list[str]:
    """
    Kaynak/hedef fabrika id'lerinin waste_streams + processes ile tutarlı olup olmadığını kontrol eder.

    Dönüş: boş liste = sorun yok; aksi halde insan okunur uyarı satırları (en fazla 50).
    """
    issues: list[str] = []
    if matches is None or matches.empty:
        return issues
    need_m = {"waste_id", "process_id", "source_factory", "target_factory"}
    if not need_m.issubset(matches.columns):
        return [f"validate: matches'te eksik sütun: {need_m - set(matches.columns)}"]

    proc = processes.copy()
    if "process_id" not in proc.columns or "factory_id" not in proc.columns:
        return ["validate: processes.csv içinde process_id ve factory_id gerekli."]
    proc["process_id"] = proc["process_id"].astype(str).str.strip()
    proc["factory_id"] = proc["factory_id"].map(parse_factory_id)
    pmap = proc.drop_duplicates(subset=["process_id"], keep="last").set_index("process_id")[
        "factory_id"
    ]

    ws = waste_streams.copy()
    if "waste_id" not in ws.columns or "process_id" not in ws.columns:
        return ["validate: waste_streams içinde waste_id ve process_id gerekli."]
    ws["waste_id"] = ws["waste_id"].astype(str).str.strip()
    ws["process_id"] = ws["process_id"].astype(str).str.strip()
    wsrc = ws.drop_duplicates(subset=["waste_id"], keep="last").set_index("waste_id")["process_id"]

    for idx, row in matches.iterrows():
        wid = str(row.get("waste_id", "")).strip()
        pid = str(row.get("process_id", "")).strip()
        sf = parse_factory_id(row.get("source_factory"))
        tf = parse_factory_id(row.get("target_factory"))
        exp_src_proc = wsrc.get(wid)
        if exp_src_proc is not None and str(exp_src_proc).strip():
            exp_sf = pmap.get(str(exp_src_proc).strip())
            if exp_sf is not None and sf is not None and int(exp_sf) != int(sf):
                issues.append(
                    f"satır {idx}: waste_id={wid} için kaynak fabrika {sf} beklenen {int(exp_sf)} "
                    f"(üretici proses {exp_src_proc})"
                )
        exp_tf = pmap.get(pid)
        if exp_tf is not None and tf is not None and int(exp_tf) != int(tf):
            issues.append(
                f"satır {idx}: hedef process_id={pid} için target_factory={tf} beklenen {int(exp_tf)}"
            )
        if len(issues) >= 50:
            issues.append("… (en fazla 50 uyarı)")
            break
    return issues
