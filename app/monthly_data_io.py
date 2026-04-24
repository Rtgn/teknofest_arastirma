"""
Aylik girdi dosyalari (factory_status, process_status, capacity_factors, process_capacity.csv)
okuma / yazma ve eksik ay satirlarini tamamlama.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.factory_ids import parse_factory_id

DEFAULT_TON_PER_DAY = 10.0
MONTHS = tuple(range(1, 13))


def _factory_id_col(df: pd.DataFrame) -> str:
    for c in ("id", "factory_id", "fabrika_id", "tesis_id"):
        if c in df.columns:
            return c
    raise ValueError("factories.csv: id / factory_id sütunu yok")


def _load_factories_labels(rt: Path) -> tuple[dict[int, str], list[int]]:
    p = rt / "factories.csv"
    if not p.is_file():
        return {}, []
    df = pd.read_csv(p)
    id_c = _factory_id_col(df)
    name_c = "name" if "name" in df.columns else id_c
    labels: dict[int, str] = {}
    ids: list[int] = []
    for _, row in df.iterrows():
        fid = parse_factory_id(row[id_c])
        if fid is None:
            continue
        ids.append(fid)
        labels[fid] = str(row.get(name_c, fid))
    return labels, ids


def _load_process_ids(rt: Path) -> tuple[dict[str, str], list[str]]:
    p = rt / "processes.csv"
    if not p.is_file():
        return {}, []
    df = pd.read_csv(p)
    if "process_id" not in df.columns:
        return {}, []
    name_c = "process_name" if "process_name" in df.columns else "process_id"
    labels: dict[str, str] = {}
    ids: list[str] = []
    for _, row in df.iterrows():
        pid = str(row.get("process_id", "")).strip()
        if not pid:
            continue
        ids.append(pid)
        labels[pid] = str(row.get(name_c, pid))
    return labels, ids


def _read_table(rt: Path, name: str) -> pd.DataFrame:
    p = rt / name
    if not p.is_file():
        return pd.DataFrame()
    return pd.read_csv(p)


def _normalize_factory_status(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["factory_id", "month", "status"])
    out = df.copy()
    out["factory_id"] = out["factory_id"].map(lambda x: parse_factory_id(x))
    out["month"] = pd.to_numeric(out["month"], errors="coerce").fillna(0).astype(int)
    out["status"] = pd.to_numeric(out["status"], errors="coerce").fillna(1.0)
    out = out.dropna(subset=["factory_id"])
    out["factory_id"] = out["factory_id"].astype(int)
    return out[["factory_id", "month", "status"]]


def _normalize_process_status(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["process_id", "month", "status"])
    out = df.copy()
    out["process_id"] = out["process_id"].astype(str).str.strip()
    out["month"] = pd.to_numeric(out["month"], errors="coerce").fillna(0).astype(int)
    out["status"] = pd.to_numeric(out["status"], errors="coerce").fillna(1.0)
    return out[["process_id", "month", "status"]]


def _normalize_capacity_factors(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["factory_id", "month", "capacity_factor"])
    out = df.copy()
    out["factory_id"] = out["factory_id"].map(lambda x: parse_factory_id(x))
    out["month"] = pd.to_numeric(out["month"], errors="coerce").fillna(0).astype(int)
    out["capacity_factor"] = pd.to_numeric(out["capacity_factor"], errors="coerce").fillna(1.0)
    out = out.dropna(subset=["factory_id"])
    out["factory_id"] = out["factory_id"].astype(int)
    return out[["factory_id", "month", "capacity_factor"]]


def load_monthly_inputs(rt: Path) -> dict[str, Any]:
    """Tüm aylık girdileri ve satır etiketleri için kaynak listeleri döndürür."""
    rt = Path(rt)
    err: list[str] = []
    fac_labels, fac_ids = _load_factories_labels(rt)
    proc_labels, proc_ids = _load_process_ids(rt)

    fs = _normalize_factory_status(_read_table(rt, "factory_status.csv"))
    ps = _normalize_process_status(_read_table(rt, "process_status.csv"))
    cf = _normalize_capacity_factors(_read_table(rt, "capacity_factors.csv"))

    cap_rows: list[dict[str, Any]] = []
    cap_path = rt / "process_capacity.csv"
    if cap_path.is_file():
        try:
            cdf = pd.read_csv(cap_path, sep=";", decimal=",")
            if "process_id" not in cdf.columns or "capacity_ton_per_day" not in cdf.columns:
                err.append("process_capacity.csv: process_id ve capacity_ton_per_day gerekli")
            else:
                cdf = cdf.copy()
                cdf["process_id"] = cdf["process_id"].astype(str).str.strip()
                cdf["capacity_ton_per_day"] = (
                    pd.to_numeric(
                        cdf["capacity_ton_per_day"].astype(str).str.replace(",", "."),
                        errors="coerce",
                    ).fillna(DEFAULT_TON_PER_DAY)
                )
                cap_rows = cdf[["process_id", "capacity_ton_per_day"]].to_dict(orient="records")
        except Exception as e:
            err.append(f"process_capacity.csv: {e}")
    else:
        err.append("process_capacity.csv bulunamadı (işlem listesinden oluşturulabilir)")

    return {
        "factory_status": fs.to_dict(orient="records"),
        "process_status": ps.to_dict(orient="records"),
        "capacity_factors": cf.to_dict(orient="records"),
        "process_capacity": cap_rows,
        "labels": {
            "factories": {str(k): v for k, v in fac_labels.items()},
            "processes": proc_labels,
        },
        "factory_ids": fac_ids,
        "process_ids": proc_ids,
        "errors": err,
    }


def _df_from_records(name: str, records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def save_factory_status(rt: Path, records: list[dict[str, Any]]) -> None:
    rt = Path(rt)
    df = _normalize_factory_status(_df_from_records("factory_status", records))
    rt.mkdir(parents=True, exist_ok=True)
    df.to_csv(rt / "factory_status.csv", index=False)


def save_process_status(rt: Path, records: list[dict[str, Any]]) -> None:
    rt = Path(rt)
    df = _normalize_process_status(_df_from_records("process_status", records))
    rt.mkdir(parents=True, exist_ok=True)
    df.to_csv(rt / "process_status.csv", index=False)


def save_capacity_factors(rt: Path, records: list[dict[str, Any]]) -> None:
    rt = Path(rt)
    df = _normalize_capacity_factors(_df_from_records("capacity_factors", records))
    rt.mkdir(parents=True, exist_ok=True)
    df.to_csv(rt / "capacity_factors.csv", index=False)


def save_process_capacity_csv(rt: Path, records: list[dict[str, Any]]) -> None:
    rt = Path(rt)
    if not records:
        raise ValueError("process_capacity boş olamaz")
    df = pd.DataFrame(records)
    if "process_id" not in df.columns or "capacity_ton_per_day" not in df.columns:
        raise ValueError("process_capacity: process_id ve capacity_ton_per_day gerekli")
    df = df.copy()
    df["process_id"] = df["process_id"].astype(str).str.strip()
    df["capacity_ton_per_day"] = pd.to_numeric(df["capacity_ton_per_day"], errors="coerce").fillna(
        DEFAULT_TON_PER_DAY
    )
    df = df[["process_id", "capacity_ton_per_day"]].drop_duplicates(subset=["process_id"], keep="last")
    rt.mkdir(parents=True, exist_ok=True)
    df.to_csv(rt / "process_capacity.csv", sep=";", index=False, decimal=".")


def ensure_monthly_grids(
    rt: Path,
    *,
    default_status: float = 1.0,
    default_cap_factor: float = 1.0,
) -> dict[str, Any]:
    """
    factories.csv / processes.csv listelerine göre eksik (fabrika|proses × ay) satırlarını ekler.
    process_capacity.csv'de eksik proseslere DEFAULT_TON_PER_DAY yazar.
    """
    rt = Path(rt)
    messages: list[str] = []
    _, fac_ids = _load_factories_labels(rt)
    _, proc_ids = _load_process_ids(rt)
    if not fac_ids:
        return {"status": "failed", "error": "factories.csv yok veya fabrika okunamadı", "messages": messages}
    if not proc_ids:
        return {"status": "failed", "error": "processes.csv yok veya proses okunamadı", "messages": messages}

    fs = _normalize_factory_status(_read_table(rt, "factory_status.csv"))
    ps = _normalize_process_status(_read_table(rt, "process_status.csv"))
    cf = _normalize_capacity_factors(_read_table(rt, "capacity_factors.csv"))

    fs_keys = set(zip(fs["factory_id"], fs["month"])) if not fs.empty else set()
    added_fs = 0
    for fid, mo in product(fac_ids, MONTHS):
        if (fid, mo) not in fs_keys:
            fs = pd.concat(
                [fs, pd.DataFrame([{"factory_id": fid, "month": mo, "status": default_status}])],
                ignore_index=True,
            )
            fs_keys.add((fid, mo))
            added_fs += 1

    ps_keys = set(zip(ps["process_id"], ps["month"])) if not ps.empty else set()
    added_ps = 0
    for pid, mo in product(proc_ids, MONTHS):
        if (pid, mo) not in ps_keys:
            ps = pd.concat(
                [ps, pd.DataFrame([{"process_id": pid, "month": mo, "status": default_status}])],
                ignore_index=True,
            )
            ps_keys.add((pid, mo))
            added_ps += 1

    cf_keys = set(zip(cf["factory_id"], cf["month"])) if not cf.empty else set()
    added_cf = 0
    for fid, mo in product(fac_ids, MONTHS):
        if (fid, mo) not in cf_keys:
            cf = pd.concat(
                [
                    cf,
                    pd.DataFrame(
                        [{"factory_id": fid, "month": mo, "capacity_factor": default_cap_factor}]
                    ),
                ],
                ignore_index=True,
            )
            cf_keys.add((fid, mo))
            added_cf += 1

    fs = fs.sort_values(["factory_id", "month"]).reset_index(drop=True)
    ps = ps.sort_values(["process_id", "month"]).reset_index(drop=True)
    cf = cf.sort_values(["factory_id", "month"]).reset_index(drop=True)

    save_factory_status(rt, fs.to_dict(orient="records"))
    save_process_status(rt, ps.to_dict(orient="records"))
    save_capacity_factors(rt, cf.to_dict(orient="records"))
    messages.append(
        f"factory_status: {added_fs} yeni satır; process_status: {added_ps}; capacity_factors: {added_cf}."
    )

    cap_path = rt / "process_capacity.csv"
    cap_df = pd.DataFrame()
    if cap_path.is_file():
        try:
            cap_df = pd.read_csv(cap_path, sep=";", decimal=",")
        except Exception:
            cap_df = pd.DataFrame()
    existing_p = set()
    if not cap_df.empty and "process_id" in cap_df.columns:
        cap_df = cap_df.copy()
        cap_df["process_id"] = cap_df["process_id"].astype(str).str.strip()
        existing_p = set(cap_df["process_id"].tolist())

    added_cap = 0
    rows: list[dict[str, Any]] = []
    if not cap_df.empty and "capacity_ton_per_day" in cap_df.columns:
        for _, r in cap_df.iterrows():
            rows.append(
                {
                    "process_id": str(r["process_id"]).strip(),
                    "capacity_ton_per_day": float(
                        pd.to_numeric(str(r["capacity_ton_per_day"]).replace(",", "."), errors="coerce")
                        or DEFAULT_TON_PER_DAY
                    ),
                }
            )
    for pid in proc_ids:
        if pid not in existing_p:
            rows.append({"process_id": pid, "capacity_ton_per_day": DEFAULT_TON_PER_DAY})
            added_cap += 1
    if rows:
        save_process_capacity_csv(rt, rows)
    messages.append(f"process_capacity.csv: {added_cap} yeni proses satırı (varsayılan {DEFAULT_TON_PER_DAY} ton/gün).")

    return {"status": "success", "messages": messages}


def explain_capacity_monthly_kg(
    capacity_ton_per_day: float,
    factory_status: float,
    process_status: float,
    capacity_factor: float,
) -> dict[str, Any]:
    """UI için sayısal açıklama: kg/ay üretim formülü."""
    base_kg = float(capacity_ton_per_day) * 1000.0 * 30.0
    combined = base_kg * factory_status * process_status * capacity_factor
    return {
        "capacity_ton_per_day": capacity_ton_per_day,
        "base_kg_month": round(base_kg, 3),
        "formula": "capacity_monthly_kg = capacity_ton_per_day × 1000 × 30 × factory_status × process_status × capacity_factor",
        "example_all_ones": round(float(capacity_ton_per_day) * 1000.0 * 30.0, 3),
        "note": "Örn. 10 ton/gün ve tüm çarpanlar 1 ise: 10 × 1000 × 30 = 300000 kg/ay.",
        "combined_kg_month": round(combined, 3),
    }
