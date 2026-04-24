"""
factories + processes + waste_streams → waste_process_links.csv (kartesyen adaylar).

Pipeline başında çalıştırılır; `matches_ready_builder` bu dosyadan matches_LCA_ready üretir.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from core.config import (
    ENV_SKIP_WASTE_LINKS_AUTOGEN,
    RUNTIME_DIR,
    allow_self_symbiosis,
)
from core.matches_ready_builder import (
    _as_str_id,
    _is_auxiliary,
    _read_table,
    haversine_km,
)

logger = logging.getLogger(__name__)

ENV_EXCLUDE_SAME_PROCESS = "WASTE_LINKS_EXCLUDE_SAME_PROCESS"


def _resolve_factory_column(processes: pd.DataFrame) -> str:
    """factory_id / fabrika_id / yazım varyantları."""
    cols_lower = {str(c).strip().lower().replace(" ", "_"): c for c in processes.columns}
    for key in ("factory_id", "fabrika_id", "factoryid", "id_fabrika"):
        if key in cols_lower:
            return cols_lower[key]
    for c in processes.columns:
        cl = str(c).strip().lower()
        if "factory" in cl and "id" in cl.replace(" ", ""):
            return c
    raise ValueError(
        "processes.csv içinde fabrika sütunu bulunamadı; "
        "beklenen: factory_id veya fabrika_id (veya benzeri)."
    )


def _coerce_factory_id_scalar(val: Any) -> float:
    """factory_id hücresi → float; geçersiz/boş → NaN."""
    if val is None:
        return np.nan
    if isinstance(val, float) and pd.isna(val):
        return np.nan
    if isinstance(val, (int, np.integer)):
        return float(int(val))
    if isinstance(val, (float, np.floating)) and not pd.isna(val):
        if np.isfinite(val):
            return float(int(val)) if val == int(val) else float(val)
        return np.nan
    s = str(val).strip().replace("\u00a0", " ")
    if not s or s.lower() in ("nan", "none", "-", "—", "#n/a", "#yok"):
        return np.nan
    s = s.replace(" ", "").replace(",", ".")
    try:
        return float(int(float(s)))
    except (ValueError, TypeError):
        m = re.search(r"-?\d+", s)
        if m:
            try:
                return float(int(m.group(0)))
            except ValueError:
                pass
    return np.nan


def _loc_scalar_factory(proc_index: pd.DataFrame, pid: str) -> float:
    """Yinelenen index satırlarında dolu factory_id (tercihen son dolu)."""
    loc = proc_index.loc[pid]
    if isinstance(loc, pd.DataFrame):
        s = loc["factory_id"].dropna()
        if s.empty:
            return np.nan
        v = s.iloc[-1]
        return float(v) if pd.notna(v) else np.nan
    v = loc["factory_id"]
    return float(v) if pd.notna(v) else np.nan


def _resolve_factories_id_column(factories: pd.DataFrame) -> str:
    """factories tablosu birincil anahtar: id, factory_id, fabrika_id, …"""
    cols_lower = {str(c).strip().lower().replace(" ", "_"): c for c in factories.columns}
    for key in ("id", "factory_id", "fabrika_id", "factoryid", "tesis_id", "fabrika_no"):
        if key in cols_lower:
            return cols_lower[key]
    for c in factories.columns:
        cl = str(c).strip().lower()
        if cl in ("id", "no", "#"):
            return c
    raise ValueError(
        "factories.csv içinde fabrika kimlik sütunu yok; beklenen: id veya factory_id / fabrika_id."
    )


def _resolve_lat_lng_columns(factories: pd.DataFrame) -> tuple[str, str]:
    cols_lower = {str(c).strip().lower().replace(" ", "_"): c for c in factories.columns}
    pairs = (
        ("lat", "lng"),
        ("latitude", "longitude"),
        ("enlem", "boylam"),
        ("y", "x"),
    )
    for a, b in pairs:
        if a in cols_lower and b in cols_lower:
            return cols_lower[a], cols_lower[b]
    if "lat" in factories.columns and "lng" in factories.columns:
        return "lat", "lng"
    raise ValueError(
        "factories.csv: enlem/boylam için lat/lng veya latitude/longitude veya enlem/boylam gerekli."
    )


def _prepare_factories_fac_map(factories: pd.DataFrame) -> pd.DataFrame:
    id_col = _resolve_factories_id_column(factories)
    lat_c, lng_c = _resolve_lat_lng_columns(factories)
    fac = factories.copy()
    fac["_fid"] = fac[id_col].map(_coerce_factory_id_scalar)
    fac = fac.dropna(subset=["_fid"])
    fac["_fid"] = fac["_fid"].astype(int)
    fac = fac.drop_duplicates(subset=["_fid"], keep="first")
    out = fac.set_index("_fid")[[lat_c, lng_c]].apply(pd.to_numeric, errors="coerce")
    out = out.rename(columns={lat_c: "lat", lng_c: "lng"})
    return out.dropna(subset=["lat", "lng"], how="any")


def _coords_or_raise(fac_map: pd.DataFrame, fid: int, *, context: str) -> tuple[float, float]:
    try:
        row = fac_map.loc[int(fid)]
        la = float(row["lat"])
        lo = float(row["lng"])
        if pd.isna(la) or pd.isna(lo):
            raise KeyError(fid)
        return la, lo
    except KeyError:
        avail = sorted({int(x) for x in fac_map.index.tolist() if pd.notna(x)})[:25]
        raise ValueError(
            f"{context}: factory_id={fid} factories.csv fabrika listesinde yok. "
            f"processes.factory_id ile factories dosyasındaki kimlik sütunu (id) aynı numaraları kullanmalı. "
            f"Örnek mevcut fabrika id'leri: {avail}"
        ) from None


def _assert_factory_sets_align(proc: pd.DataFrame, fac_map: pd.DataFrame) -> None:
    """Tam uyumsuzluk varsa tek mesajda hata (1,2,3 vs 101,102…)."""
    pf = {int(x) for x in proc["factory_id"].dropna().unique()}
    ff = {int(x) for x in fac_map.index.unique()}
    if not pf or not ff:
        return
    if pf.isdisjoint(ff):
        raise ValueError(
            "processes.csv içindeki factory_id değerlerinin hiçbiri factories.csv "
            "fabrika kimlikleriyle eşleşmiyor.\n"
            f"  processes.factory_id örnekleri: {sorted(pf)[:25]}\n"
            f"  factories id örnekleri: {sorted(ff)[:25]}\n"
            "İki dosyada aynı fabrika numaralandırmasını kullanın (örn. her ikisinde de 101, 102 …) "
            "veya processes içindeki factory_id sütununu factories ile hizalayın."
        )


def _prepare_processes_dataframe(processes: pd.DataFrame) -> pd.DataFrame:
    """process_id normalize, fabrika sütunu çöz, yinelenen process_id → dolu factory öncelikli tek satır."""
    proc = processes.copy()
    proc["process_id"] = proc["process_id"].map(_as_str_id)
    fc = _resolve_factory_column(proc)
    proc["factory_id"] = proc[fc].map(_coerce_factory_id_scalar)
    proc = proc[proc["process_id"] != ""]
    proc["_has_fab"] = proc["factory_id"].notna()
    proc = proc.sort_values(["process_id", "_has_fab"], ascending=[True, False])
    proc = proc.drop_duplicates(subset=["process_id"], keep="first")
    proc = proc.drop(columns=["_has_fab"], errors="ignore")
    return proc


def physical_state_to_transport_mode(ps: Any) -> str:
    """solid/liquid/gas (+ Türkçe) → tanker / truck / pipeline / truck."""
    s = str(ps).strip().lower()
    if s in ("gas", "gaz"):
        return "pipeline"
    if s in ("liquid", "sıvı", "sivi"):
        return "tanker"
    if s in ("solid", "katı", "kati"):
        return "truck"
    if "gas" in s or "gaz" in s:
        return "pipeline"
    if "liquid" in s or "sıvı" in s or "sivi" in s:
        return "tanker"
    if "solid" in s or "katı" in s or "kati" in s:
        return "truck"
    return "truck"


def _waste_amount_base_from_streams_row(row: pd.Series) -> float:
    if "waste_amount_base" in row.index:
        v = row.get("waste_amount_base")
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            return float(pd.to_numeric(v, errors="coerce") or 0.0)
    return 0.0


def build_waste_process_links_dataframe(
    runtime: Path,
    *,
    period: Optional[str] = None,
    exclude_same_process: Optional[bool] = None,
    allow_self_symbiosis_flag: Optional[bool] = None,
) -> pd.DataFrame:
    """
    Her waste_id için tüm (yardımcı olmayan) hedef proseslerle satır üretir.

    Kaynak proses ``processes.csv`` / fabrika koordinatları ile çözülemeyen atık
    satırları **atlanır** (hata verilmez); yalnızca geçerli kaynaklar için aday üretilir.
    """
    runtime = Path(runtime)
    factories = _read_table(runtime / "factories.csv")
    processes = _read_table(runtime / "processes.csv")
    waste_streams = _read_table(runtime / "waste_streams.csv")

    if "process_id" not in processes.columns:
        raise ValueError("processes.csv: process_id gerekli")
    if "waste_id" not in waste_streams.columns or "process_id" not in waste_streams.columns:
        raise ValueError("waste_streams.csv: waste_id, process_id (kaynak) gerekli")
    if "physical_state" not in waste_streams.columns:
        raise ValueError("waste_streams.csv: physical_state gerekli")

    try:
        fac_map = _prepare_factories_fac_map(factories)
    except ValueError as e:
        raise ValueError(f"factories.csv: {e}") from e

    try:
        proc = _prepare_processes_dataframe(processes)
    except ValueError as e:
        raise ValueError(f"processes.csv fabrika sütunu: {e}") from e

    _assert_factory_sets_align(proc, fac_map)

    aux_col = "is_auxiliary_process" if "is_auxiliary_process" in proc.columns else None
    proc_index = proc.set_index("process_id", drop=False)

    def _aux_ok(pid: str) -> bool:
        if not aux_col:
            return True
        loc = proc_index.loc[pid]
        if isinstance(loc, pd.DataFrame):
            v = loc[aux_col].iloc[-1]
        else:
            v = loc[aux_col]
        return not _is_auxiliary(v)

    target_ids = [pid for pid in proc["process_id"].tolist() if pid and _aux_ok(pid)]

    if exclude_same_process is None:
        exclude_same_process = os.environ.get(ENV_EXCLUDE_SAME_PROCESS, "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    if allow_self_symbiosis_flag is None:
        allow_self_symbiosis_flag = allow_self_symbiosis()

    if period:
        cap_path = runtime / f"process_capacity_monthly_{period}.csv"
        if cap_path.is_file():
            logger.info("İsteğe bağlı kapasite dosyası mevcut (şimdilik yalnızca bilgi): %s", cap_path.name)

    ws = waste_streams.copy(deep=True)
    ws.loc[:, "waste_id"] = ws["waste_id"].map(_as_str_id)
    ws.loc[:, "source_process_id"] = ws["process_id"].map(_as_str_id)

    rows_out: list[dict[str, Any]] = []
    match_id = 0

    for waste_id, grp in ws.groupby("waste_id", sort=False):
        if not waste_id:
            continue
        row0 = grp.iloc[0]
        src_proc = _as_str_id(row0["source_process_id"])
        if not src_proc:
            logger.warning("waste_id=%s: kaynak process_id boş, atlanıyor", waste_id)
            continue
        if src_proc not in proc_index.index:
            logger.warning(
                "waste_id=%s: kaynak proses processes.csv içinde tanımlı değil (%s), atlanıyor",
                waste_id,
                src_proc,
            )
            continue
        src_f = _loc_scalar_factory(proc_index, src_proc)
        if pd.isna(src_f):
            logger.warning(
                "waste_id=%s: kaynak proses için factory_id yok (%s), atlanıyor",
                waste_id,
                src_proc,
            )
            continue
        src_f = int(src_f)

        w_base = _waste_amount_base_from_streams_row(row0)
        phys = row0.get("physical_state")

        try:
            la1, lo1 = _coords_or_raise(fac_map, src_f, context="Kaynak fabrika")
        except ValueError as e:
            logger.warning("waste_id=%s: %s", waste_id, e)
            continue

        tm = physical_state_to_transport_mode(phys)

        for tgt in target_ids:
            if exclude_same_process and tgt == src_proc:
                continue
            if not _aux_ok(tgt):
                continue
            tgt_f = _loc_scalar_factory(proc_index, tgt)
            if pd.isna(tgt_f):
                continue
            tgt_f = int(tgt_f)
            if not allow_self_symbiosis_flag and src_f == tgt_f:
                continue
            try:
                la2, lo2 = _coords_or_raise(fac_map, tgt_f, context="Hedef fabrika")
            except ValueError as e:
                logger.warning("Hedef atlanıyor (%s): %s", tgt, e)
                continue

            dist = round(haversine_km(la1, lo1, la2, lo2), 4)

            rows_out.append(
                {
                    "waste_id": waste_id,
                    "source_process_id": src_proc,
                    "source_factory_id": src_f,
                    "target_process_id": tgt,
                    "target_factory_id": tgt_f,
                    "waste_amount_base": w_base,
                    "distance_km": dist,
                    "transport_mode": tm,
                    "match_id": match_id,
                }
            )
            match_id += 1

    if not rows_out:
        raise ValueError(
            "waste_process_links: üretilen satır yok. Kaynaklar için processes.csv içinde "
            "factory_id (veya fabrika_id) dolu olmalı; yinelenen process_id satırlarında "
            "boş olmayan fabrika değeri tercih edilir. factories.csv id ile eşleşmeli."
        )

    df_out = pd.DataFrame(rows_out)
    tgt_fac = pd.to_numeric(df_out["target_factory_id"], errors="coerce").dropna().unique()
    if len(tgt_fac) == 1:
        logger.warning(
            "waste_process_links: Tüm hedef satırlar tek fabrikaya (factory_id=%s). "
            "Birden fazla hedef tesis için processes.csv içinde her alıcı prosesin "
            "factory_id / fabrika_id değerini ilgili tesis numarasına güncelleyin; "
            "bu numaralar factories.csv `id` sütunu ile birebir aynı olmalı.",
            int(tgt_fac[0]),
        )
    return df_out


def write_waste_process_links_excel(
    runtime: Path,
    *,
    period: Optional[str] = None,
    exclude_same_process: Optional[bool] = None,
    allow_self_symbiosis_flag: Optional[bool] = None,
) -> Path:
    runtime = Path(runtime)
    df = build_waste_process_links_dataframe(
        runtime,
        period=period,
        exclude_same_process=exclude_same_process,
        allow_self_symbiosis_flag=allow_self_symbiosis_flag,
    )
    out = runtime / "waste_process_links.csv"
    runtime.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    logger.info("waste_process_links.csv yazıldı: %s (%s satır)", out, len(df))
    return out


def try_generate_waste_process_links(
    runtime: Path,
    period: str,
    *,
    exclude_same_process: Optional[bool] = None,
    allow_self_symbiosis_flag: Optional[bool] = None,
) -> Optional[Path]:
    """
    Gerekli üç dosya varsa waste_process_links.csv üretir; aksi halde None.

    ``SYMBIOSIS_SKIP_WASTE_LINKS_AUTOGEN=1`` → otomatik üretimi atla (elle düzenlenmiş dosyayı koru).

    Varsayılan: self-simbiyoz kapalı. ``SYMBIOSIS_ALLOW_SELF_SYMBIOSIS=1`` ile aynı fabrika içi satırlar üretilir.
    """
    runtime = Path(runtime)
    if os.environ.get(ENV_SKIP_WASTE_LINKS_AUTOGEN, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        logger.info("waste_process_links otomatik üretim kapalı (%s)", ENV_SKIP_WASTE_LINKS_AUTOGEN)
        return None

    needed = ("factories.csv", "processes.csv", "waste_streams.csv")
    if not all((runtime / f).is_file() for f in needed):
        logger.info(
            "waste_process_links otomatik üretim atlandı (eksik: %s)",
            [f for f in needed if not (runtime / f).is_file()],
        )
        return None
    try:
        return write_waste_process_links_excel(
            runtime,
            period=period,
            exclude_same_process=exclude_same_process,
            allow_self_symbiosis_flag=allow_self_symbiosis_flag,
        )
    except Exception as e:
        logger.exception("waste_process_links üretilemedi: %s", e)
        raise


if __name__ == "__main__":
    import argparse
    import sys

    _V2 = Path(__file__).resolve().parent.parent
    if str(_V2) not in sys.path:
        sys.path.insert(0, str(_V2))

    p = argparse.ArgumentParser(description="waste_process_links.csv üret")
    p.add_argument(
        "--runtime",
        type=Path,
        default=RUNTIME_DIR,
        help="outputs/runtime dizini",
    )
    p.add_argument("--period", type=str, default=None, help="process_capacity_monthly_{period}.csv için YYYY-MM")
    p.add_argument(
        "--exclude-same-process",
        action="store_true",
        help="Kaynak ve hedef proses aynıysa satır üretme",
    )
    p.add_argument(
        "--no-self-symbiosis",
        action="store_true",
        help="Self-simbiyoz satırlarını üretme (varsayılan zaten kapalı; zorunlu kapatma için)",
    )
    args = p.parse_args()
    path = write_waste_process_links_excel(
        args.runtime,
        period=args.period,
        exclude_same_process=args.exclude_same_process if args.exclude_same_process else None,
        allow_self_symbiosis_flag=False if args.no_self_symbiosis else None,
    )
    print(path)
