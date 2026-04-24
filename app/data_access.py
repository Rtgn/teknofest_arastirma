"""
outputs/runtime altindaki Excel/CSV dosyalarini okuyarak UI verilerini hazirlar.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.config import RUNTIME_DIR
from core.factory_ids import parse_factory_id
from core.period import (
    matches_lca_filename,
    parse_period,
    process_capacity_monthly_filename,
    selected_matches_filename,
)
from optimization.result_reader import (
    SELECTED_MATCHES_CSV,
    extract_selected_rows,
    normalize_match_id,
    read_selected_match_ids,
)


def runtime_dir() -> Path:
    return Path(RUNTIME_DIR)


def exclude_period_from_ui(period: str) -> bool:
    """Arşiv/yedek eşleşme dosyaları (adında veya dönemde *eski*) ağ/simülasyon listelerinde gösterilmez."""
    return "eski" in str(period).strip().lower()


def list_periods_from_runtime(rt: Optional[Path] = None) -> list[str]:
    """matches_LCA_<periyot>.xlsx dosya adlarından periyot listesi (baz ay ve __SIM senaryoları)."""
    base = Path(rt) if rt else runtime_dir()
    if not base.is_dir():
        return []
    out: list[str] = []
    for p in base.glob("matches_LCA_*.xlsx"):
        m = re.search(r"matches_LCA_(.+)\.xlsx$", p.name, re.I)
        if m:
            per = m.group(1).strip()
            if not exclude_period_from_ui(per):
                out.append(per)
    return sorted(set(out))


def _factory_id_column(df: pd.DataFrame) -> str:
    for c in ("id", "factory_id", "fabrika_id", "tesis_id"):
        if c in df.columns:
            return c
    raise ValueError("factories: id / factory_id sütunu yok")


def _lat_lng_columns(df: pd.DataFrame) -> tuple[str, str]:
    lower = {str(x).strip().lower(): x for x in df.columns}
    if "lat" in lower and "lng" in lower:
        return lower["lat"], lower["lng"]
    if "latitude" in lower and "longitude" in lower:
        return lower["latitude"], lower["longitude"]
    raise ValueError("factories: lat/lng veya latitude/longitude yok")


def load_factories_map(rt: Optional[Path] = None) -> dict[int, dict[str, Any]]:
    base = Path(rt) if rt else runtime_dir()
    path = base / "factories.xlsx"
    if not path.is_file():
        return {}
    try:
        df = pd.read_excel(path, engine="openpyxl")
        id_c = _factory_id_column(df)
        lat_c, lng_c = _lat_lng_columns(df)
    except Exception:
        return {}
    name_c = "name" if "name" in df.columns else id_c
    out: dict[int, dict[str, Any]] = {}
    for _, row in df.iterrows():
        fid = parse_factory_id(row[id_c])
        if fid is None:
            continue
        out[fid] = {
            "id": fid,
            "name": str(row.get(name_c, fid)),
            "lat": float(pd.to_numeric(row[lat_c], errors="coerce") or 0),
            "lng": float(pd.to_numeric(row[lng_c], errors="coerce") or 0),
        }
    return out


# Tahmini harita yerleşimi (factories.xlsx yok / eksik id): Anadolu yaklaşık merkez
_SYNTH_CENTER_LAT = 39.0
_SYNTH_CENTER_LNG = 35.0
_SYNTH_RADIUS_DEG = 0.45


def _parallel_segment_offset(
    lat0: float,
    lng0: float,
    lat1: float,
    lng1: float,
    *,
    rank: int,
    n_parallel: int,
    step_deg: float = 0.00032,
) -> tuple[float, float, float, float]:
    """
    Aynı (kaynak, hedef) çiftindeki çoklu eşleşmeleri ayırmak için segmenti paralel kaydırır.
    rank: 0..n_parallel-1; tek çizgide rank=0 ve ofset=0.
    """
    if n_parallel <= 1:
        return lat0, lng0, lat1, lng1
    dx = lng1 - lng0
    dy = lat1 - lat0
    L = math.hypot(dx, dy)
    if L < 1e-12:
        ang = 2.0 * math.pi * rank / max(n_parallel, 1)
        r = step_deg * 3.0
        return (
            lat0 + r * math.sin(ang),
            lng0 + r * math.cos(ang),
            lat1 + r * math.sin(ang),
            lng1 + r * math.cos(ang),
        )
    px = -dy / L
    py = dx / L
    mid = 0.5 * (n_parallel - 1)
    off = (float(rank) - mid) * step_deg
    return (
        lat0 + py * off,
        lng0 + px * off,
        lat1 + py * off,
        lng1 + px * off,
    )


def augment_factories_for_used_ids(
    factories: dict[int, dict[str, Any]],
    used: set[int],
) -> tuple[dict[int, dict[str, Any]], bool]:
    """
    Eksik fabrika kimlikleri için dairesel yerleşim ile lat/lng üretir.
    Dönüş: (tam harita, coordinates_estimated)
    """
    out = {k: dict(v) for k, v in factories.items()}
    missing = sorted(used - set(out.keys()))
    if not missing:
        return out, False

    estimated = True
    n = len(missing)
    for i, fid in enumerate(missing):
        ang = 2.0 * math.pi * i / max(n, 1)
        lat = _SYNTH_CENTER_LAT + _SYNTH_RADIUS_DEG * math.sin(ang)
        lng = _SYNTH_CENTER_LNG + _SYNTH_RADIUS_DEG * math.cos(ang)
        out[fid] = {
            "id": fid,
            "name": f"Fabrika {fid}",
            "lat": lat,
            "lng": lng,
        }
    return out, estimated


def load_matches_for_network(
    period: str,
    *,
    source: str = "matches_lca",
    rt: Optional[Path] = None,
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    source: 'matches_lca' | 'selected'
    Dönüş: (dataframe, hata_mesajı veya None)

    Seçili görünüm: ``selected_matches_*.xlsx`` farklı ``process_id`` biçimleri içerebilir (GAMS sonrası
    üretilmiş önbellek). Bu yüzden ``selected_matches.csv`` ve güncel ``matches_LCA_*.xlsx``
    varsa satırlar her zaman bu ikisinden ``match_id`` ile birleştirilir (pipeline ile aynı).
    """
    base = Path(rt) if rt else runtime_dir()
    need = {"source_factory", "target_factory"}

    if source == "selected":
        trace_csv = base / f"selected_matches_{period}.csv"
        csv_path = trace_csv if trace_csv.is_file() else (base / SELECTED_MATCHES_CSV)
        mca_path = base / matches_lca_filename(period)
        if csv_path.is_file() and mca_path.is_file():
            try:
                ids = set(read_selected_match_ids(csv_path))
                df = extract_selected_rows(mca_path, csv_path)
                if not df.empty:
                    if not need.issubset(set(df.columns)):
                        return (
                            pd.DataFrame(),
                            f"Eksik sütun: {need - set(df.columns)}",
                        )
                    return df, None
                if ids:
                    return (
                        pd.DataFrame(),
                        f"{SELECTED_MATCHES_CSV} içindeki match_id değerleri güncel "
                        f"{matches_lca_filename(period)} ile eşleşmiyor. "
                        "waste_process_links / eşleşme tablosu değiştiyse tam pipeline'ı "
                        "(GAMS new3.gms dahil) yeniden çalıştırın; böylece seçimler yeni "
                        "match_id sırasına göre üretilir.",
                    )
                return df, None
            except Exception as e:
                return pd.DataFrame(), str(e)

        path = base / selected_matches_filename(period)
        if not path.is_file():
            return (
                pd.DataFrame(),
                f"Dosya yok: {matches_lca_filename(period)} ve {SELECTED_MATCHES_CSV} "
                f"(veya yedek {path.name})",
            )
    else:
        path = base / matches_lca_filename(period)
        if not path.is_file():
            return pd.DataFrame(), f"Dosya yok: {path.name}"

    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        return pd.DataFrame(), str(e)
    if not need.issubset(set(df.columns)):
        return (
            pd.DataFrame(),
            f"Eksik sütun: {need - set(df.columns)}",
        )
    return df, None


def build_network_payload(period: str, source: str = "matches_lca") -> dict[str, Any]:
    """Plotly / UI için node + edge listesi."""
    df, err = load_matches_for_network(period, source=source)
    if err:
        return {"period": period, "source": source, "error": err, "nodes": [], "edges": []}
    if df.empty:
        return {
            "period": period,
            "source": source,
            "error": None,
            "nodes": [],
            "edges": [],
            "stats": {"matches": 0, "co2": 0.0, "profit": 0.0, "waste_kg": 0.0},
            "coordinates_estimated": False,
        }

    wcol = "waste_amount_monthly" if "waste_amount_monthly" in df.columns else None
    if wcol is None and "waste_amount_base" in df.columns:
        wcol = "waste_amount_base"
    score_col = "sustainability_score" if "sustainability_score" in df.columns else None
    co2_col = None
    for c in ("total_CO2", "net_co2e", "process_LCA_CO2"):
        if c in df.columns:
            co2_col = c
            break
    profit_col = "profit" if "profit" in df.columns else None

    used: set[int] = set()
    for _, row in df.iterrows():
        sf = parse_factory_id(row["source_factory"])
        tf = parse_factory_id(row["target_factory"])
        if sf is not None:
            used.add(sf)
        if tf is not None:
            used.add(tf)

    if not used:
        return {
            "period": period,
            "source": source,
            "error": "Geçerli source_factory / target_factory yok.",
            "nodes": [],
            "edges": [],
            "coordinates_estimated": False,
        }

    factories_raw = load_factories_map()
    factories, coordinates_estimated = augment_factories_for_used_ids(factories_raw, used)

    pair_list: list[tuple[int, int]] = []
    for _, row in df.iterrows():
        a = parse_factory_id(row["source_factory"])
        b = parse_factory_id(row["target_factory"])
        if a is not None and b is not None:
            pair_list.append((a, b))
    pair_count = Counter(pair_list)
    pair_rank: dict[tuple[int, int], int] = defaultdict(int)

    edges: list[dict[str, Any]] = []
    out_deg: dict[int, int] = defaultdict(int)
    in_deg: dict[int, int] = defaultdict(int)

    for _, row in df.iterrows():
        src = parse_factory_id(row["source_factory"])
        tgt = parse_factory_id(row["target_factory"])
        if src is None or tgt is None:
            continue
        sf = factories.get(src)
        tf = factories.get(tgt)
        if not sf or not tf:
            continue

        w = float(pd.to_numeric(row.get(wcol), errors="coerce") or 0.0) if wcol else 0.0
        pr = float(pd.to_numeric(row.get(profit_col), errors="coerce") or 0.0) if profit_col else 0.0
        co2 = float(pd.to_numeric(row.get(co2_col), errors="coerce") or 0.0) if co2_col else 0.0
        sc = float(pd.to_numeric(row.get(score_col), errors="coerce") or 0.0) if score_col else 0.0

        key = (src, tgt)
        rank = pair_rank[key]
        pair_rank[key] = rank + 1
        n_par = pair_count[key]
        sla, slo, tla, tlo = _parallel_segment_offset(
            float(sf["lat"]),
            float(sf["lng"]),
            float(tf["lat"]),
            float(tf["lng"]),
            rank=rank,
            n_parallel=n_par,
        )

        mid = ""
        wid = ""
        if "match_id" in df.columns:
            v = row.get("match_id")
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                mid = str(v).strip()
        if "waste_id" in df.columns:
            v = row.get("waste_id")
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                wid = str(v).strip()

        edges.append(
            {
                "source": src,
                "target": tgt,
                "src_name": sf["name"],
                "tgt_name": tf["name"],
                "src_lat": sla,
                "src_lng": slo,
                "tgt_lat": tla,
                "tgt_lng": tlo,
                "weight_kg": round(w, 2),
                "profit": round(pr, 4),
                "co2_saved": round(co2, 6),
                "avg_score": round(sc, 4),
                "match_id": mid,
                "waste_id": wid,
            }
        )
        out_deg[src] += 1
        in_deg[tgt] += 1

    unique_pairs = len({(e["source"], e["target"]) for e in edges})

    nodes: list[dict[str, Any]] = []
    for fid in sorted(used):
        fac = factories.get(fid)
        if not fac:
            continue
        is_source = df["source_factory"].map(parse_factory_id).eq(fid).any()
        is_target = df["target_factory"].map(parse_factory_id).eq(fid).any()
        if is_source and is_target:
            color = "#E8A838"
        elif is_source:
            color = "#4A90E2"
        else:
            color = "#7ED321"
        nodes.append(
            {
                "id": fid,
                "name": fac["name"],
                "lat": fac["lat"],
                "lng": fac["lng"],
                "color": color,
                "out_count": int(out_deg.get(fid, 0)),
                "in_count": int(in_deg.get(fid, 0)),
            }
        )

    total_w = sum(e["weight_kg"] for e in edges)
    total_co2 = sum(e["co2_saved"] for e in edges)
    total_pr = sum(e["profit"] for e in edges)
    avg_sus: Optional[float] = None
    if score_col and score_col in df.columns:
        avg_sus = float(pd.to_numeric(df[score_col], errors="coerce").mean())
        if pd.isna(avg_sus):
            avg_sus = None

    st: dict[str, Any] = {
        "matches": len(edges),
        "matches_source_rows": len(df),
        "edges": len(edges),
        "unique_pairs": unique_pairs,
        "co2": total_co2,
        "profit": total_pr,
        "waste_kg": total_w,
    }
    if avg_sus is not None:
        st["avg_sustainability"] = round(avg_sus, 4)

    return {
        "period": period,
        "source": source,
        "error": None,
        "nodes": nodes,
        "edges": edges,
        "coordinates_estimated": coordinates_estimated,
        "stats": st,
    }


def summarize_matches_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """matches_LCA benzeri tablo için toplu metrikler (harita/kenar üretmeden)."""
    out: dict[str, Any] = {
        "rows": len(df),
        "waste_kg": 0.0,
        "co2": 0.0,
        "profit": 0.0,
        "unique_pairs": 0,
        "unique_factories": 0,
        "avg_sustainability": None,
    }
    if df is None or df.empty:
        return out
    wcol = None
    if "waste_amount_monthly" in df.columns:
        wcol = "waste_amount_monthly"
    elif "waste_amount_base" in df.columns:
        wcol = "waste_amount_base"
    if wcol:
        out["waste_kg"] = float(pd.to_numeric(df[wcol], errors="coerce").fillna(0).sum())
    co2_col = None
    for c in ("total_CO2", "net_co2e", "process_LCA_CO2"):
        if c in df.columns:
            co2_col = c
            break
    if co2_col:
        out["co2"] = float(pd.to_numeric(df[co2_col], errors="coerce").fillna(0).sum())
    if "profit" in df.columns:
        out["profit"] = float(pd.to_numeric(df["profit"], errors="coerce").fillna(0).sum())
    pairs: list[tuple[int, int]] = []
    fac_ids: set[int] = set()
    if "source_factory" in df.columns and "target_factory" in df.columns:
        for _, row in df.iterrows():
            a = parse_factory_id(row["source_factory"])
            b = parse_factory_id(row["target_factory"])
            if a is not None and b is not None:
                pairs.append((a, b))
                fac_ids.add(a)
                fac_ids.add(b)
        out["unique_pairs"] = len(set(pairs))
        out["unique_factories"] = len(fac_ids)
    if "sustainability_score" in df.columns:
        m = pd.to_numeric(df["sustainability_score"], errors="coerce").mean()
        if pd.notna(m):
            out["avg_sustainability"] = float(m)
    return out


def _read_osb_limit_kg(base: Path) -> Optional[float]:
    p = base / "osb_limit.txt"
    if not p.is_file():
        return None
    try:
        t = p.read_text(encoding="utf-8")
        m = re.search(r"OSB_Limit\s*=\s*([\d.+\-eE]+)", t)
        if m:
            return float(m.group(1))
    except Exception:
        return None
    return None


def _total_capacity_monthly_kg(period: str, base: Path) -> Optional[float]:
    path = base / process_capacity_monthly_filename(period)
    if not path.is_file():
        return None
    try:
        cdf = pd.read_excel(path, engine="openpyxl")
        if "capacity_monthly" not in cdf.columns:
            return None
        return float(pd.to_numeric(cdf["capacity_monthly"], errors="coerce").fillna(0).sum())
    except Exception:
        return None


def _latest_base_period_string(periods: list[str]) -> Optional[str]:
    """Öncelik: YYYY-MM biçimindeki son dönem; yoksa listenin son elemanı."""
    base_only = [p for p in periods if re.match(r"^\d{4}-\d{2}$", str(p).strip())]
    if base_only:
        return base_only[-1]
    return periods[-1] if periods else None


def _selected_rows_from_matches_df(df: pd.DataFrame, selected_csv: Path) -> Optional[pd.DataFrame]:
    """Aynı matches DataFrame üzerinde seçilen match_id filtrelemesi (Excel'i ikinci kez okumaz)."""
    if df is None or df.empty or not selected_csv.is_file():
        return None
    try:
        ids = set(read_selected_match_ids(selected_csv))
    except Exception:
        return None
    if not ids:
        return None
    if "match_id" in df.columns:
        key = df["match_id"].map(normalize_match_id)
    else:
        key = pd.Series([normalize_match_id(i) for i in df.index], index=df.index)
    sel = df.loc[key.isin(ids)].copy()
    return sel if not sel.empty else None


def load_dashboard_summary(rt: Optional[Path] = None) -> dict[str, Any]:
    """
    Kontrol paneli: envanter sayıları, son baz dönem için potansiyel ağ metrikleri,
    isteğe bağlı seçilen simbiyoz özeti ve OSB kapasite üst sınırı.
    """
    base = Path(rt) if rt else runtime_dir()
    periods = list_periods_from_runtime(base)
    latest = _latest_base_period_string(periods)

    inv: dict[str, Optional[int]] = {"factories": None, "processes": None, "waste_streams": None}
    fp = base / "factories.xlsx"
    if fp.is_file():
        try:
            fdf = pd.read_excel(fp, engine="openpyxl")
            inv["factories"] = int(len(fdf))
        except Exception:
            pass
    pp = base / "processes.xlsx"
    if pp.is_file():
        try:
            pdf = pd.read_excel(pp, engine="openpyxl")
            inv["processes"] = int(len(pdf))
        except Exception:
            pass
    wp = base / "waste_streams.xlsx"
    if wp.is_file():
        try:
            wdf = pd.read_excel(wp, engine="openpyxl")
            inv["waste_streams"] = int(len(wdf))
        except Exception:
            pass

    summary: dict[str, Any] = {
        "inventory": inv,
        "periods_total": len(periods),
        "latest_period": latest,
        "osb_limit_kg": _read_osb_limit_kg(base),
        "capacity_monthly_total_kg": _total_capacity_monthly_kg(latest, base) if latest else None,
        "matches_lca": None,
        "selected": None,
        "latest_error": None,
        "preview_rows": [],
    }

    if not latest:
        return summary

    df, err = load_matches_for_network(latest, source="matches_lca", rt=base)
    if err:
        summary["latest_error"] = err
    elif df is not None and not df.empty:
        summary["matches_lca"] = summarize_matches_dataframe(df)
        trace_csv = base / f"selected_matches_{latest}.csv"
        csv_path = trace_csv if trace_csv.is_file() else (base / SELECTED_MATCHES_CSV)
        sel_df = _selected_rows_from_matches_df(df, csv_path)
        if sel_df is not None:
            summary["selected"] = summarize_matches_dataframe(sel_df)
        cols = [
            c
            for c in (
                "waste_id",
                "process_id",
                "source_factory",
                "target_factory",
                "waste_amount_monthly",
                "sustainability_score",
            )
            if c in df.columns
        ]
        sub = df[cols].head(8) if cols else df.head(8)
        summary["preview_rows"] = sub.to_dict(orient="records")

    return summary


def load_simulation_baseline(period: str, rt: Optional[Path] = None) -> dict[str, Any]:
    """
    Dijital ikiz formu için: seçilen baz ay (YYYY-MM) ile fabrika / proses durumu ve kapasite özeti.
    """
    base = Path(rt) if rt else runtime_dir()
    try:
        _, month = parse_period(period)
    except ValueError as e:
        return {"error": str(e), "period": period}

    factories_out: list[dict[str, Any]] = []
    processes_out: list[dict[str, Any]] = []
    errs: list[str] = []

    fac_xlsx = base / "factories.xlsx"
    fs_xlsx = base / "factory_status.xlsx"
    if fac_xlsx.is_file() and fs_xlsx.is_file():
        try:
            fac_df = pd.read_excel(fac_xlsx, engine="openpyxl")
            fst = pd.read_excel(fs_xlsx, engine="openpyxl")
            id_c = _factory_id_column(fac_df)
            name_c = "name" if "name" in fac_df.columns else id_c
            fst_m = fst.loc[pd.to_numeric(fst["month"], errors="coerce") == month]
            fs_map: dict[int, float] = {}
            if "factory_id" in fst_m.columns and "status" in fst_m.columns:
                for _, r in fst_m.iterrows():
                    fid = parse_factory_id(r["factory_id"])
                    if fid is not None:
                        fs_map[fid] = float(pd.to_numeric(r["status"], errors="coerce") or 1.0)
            for _, row in fac_df.iterrows():
                fid = parse_factory_id(row[id_c])
                if fid is None:
                    continue
                factories_out.append(
                    {
                        "factory_id": fid,
                        "name": str(row.get(name_c, fid)),
                        "status": float(fs_map.get(fid, 1.0)),
                    }
                )
        except Exception as e:
            errs.append(f"fabrika: {e}")
    else:
        errs.append("factories.xlsx veya factory_status.xlsx yok")

    proc_xlsx = base / "processes.xlsx"
    ps_xlsx = base / "process_status.xlsx"
    cap_m = base / process_capacity_monthly_filename(period)
    cap_map: dict[str, float] = {}
    if cap_m.is_file():
        try:
            cdf = pd.read_excel(cap_m, engine="openpyxl")
            if "process_id" in cdf.columns and "capacity_monthly" in cdf.columns:
                for _, r in cdf.iterrows():
                    pid = str(r["process_id"]).strip()
                    cap_map[pid] = float(pd.to_numeric(r["capacity_monthly"], errors="coerce") or 0.0)
        except Exception as e:
            errs.append(f"kapasite dosyası: {e}")

    if proc_xlsx.is_file() and ps_xlsx.is_file():
        try:
            proc = pd.read_excel(proc_xlsx, engine="openpyxl")
            pst = pd.read_excel(ps_xlsx, engine="openpyxl")
            pst_m = pst.loc[pd.to_numeric(pst["month"], errors="coerce") == month]
            ps_map: dict[str, float] = {}
            if "process_id" in pst_m.columns and "status" in pst_m.columns:
                for _, r in pst_m.iterrows():
                    ps_map[str(r["process_id"]).strip()] = float(
                        pd.to_numeric(r["status"], errors="coerce") or 1.0
                    )
            name_pc = "process_name" if "process_name" in proc.columns else "process_id"
            for _, row in proc.iterrows():
                pid = str(row.get("process_id", "")).strip()
                if not pid:
                    continue
                processes_out.append(
                    {
                        "process_id": pid,
                        "name": str(row.get(name_pc, pid)),
                        "status": float(ps_map.get(pid, 1.0)),
                        "capacity_monthly_kg": float(cap_map.get(pid, 0.0)),
                    }
                )
        except Exception as e:
            errs.append(f"proses: {e}")
    else:
        errs.append("processes.xlsx veya process_status.xlsx yok")

    return {
        "period": period,
        "month": month,
        "factories": factories_out,
        "processes": processes_out,
        "has_capacity_file": cap_m.is_file(),
        "errors": errs,
    }
