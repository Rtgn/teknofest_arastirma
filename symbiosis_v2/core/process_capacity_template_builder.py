"""
processes_template.xlsx → process_capacity_template.csv (sabit ton/gün kapasitesi).

Şablon dizini ``DATA_SCHEMAS_DIR`` (= ``BASE_DIR / "data_schemas" / "templates"``) üzerinden tanımlıdır.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import BASE_DIR, DATA_SCHEMAS_DIR  # BASE_DIR: kök; DATA_SCHEMAS_DIR: şablonlar


def build_process_capacity_template_from_processes(
    *,
    processes_xlsx: Path | None = None,
    output_csv: Path | None = None,
    capacity_ton_per_day: float = 10.0,
) -> pd.DataFrame:
    """
    ``processes_template.xlsx`` içindeki ``process_id`` değerlerini okur (yinelenenleri tekilleştirir);
    her biri için ``capacity_ton_per_day`` atar ve ``process_capacity_template.csv`` olarak kaydeder.

    Varsayılan girdi/çıktı: ``DATA_SCHEMAS_DIR`` (= ``BASE_DIR / "data_schemas" / "templates"``).
    """
    # Yollar: DATA_SCHEMAS_DIR (= BASE_DIR / "data_schemas" / "templates", core.config)
    templates_dir = DATA_SCHEMAS_DIR
    src = processes_xlsx or (templates_dir / "processes_template.xlsx")
    dst = output_csv or (templates_dir / "process_capacity_template.csv")

    proc = pd.read_excel(src)
    if "process_id" not in proc.columns:
        raise ValueError(f"'process_id' kolonu yok: {src}")

    ids = proc["process_id"].dropna().astype(str).str.strip()
    ids = ids[ids != ""].drop_duplicates()

    out = pd.DataFrame(
        {
            "process_id": ids.values,
            "capacity_ton_per_day": float(capacity_ton_per_day),
        }
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dst, index=False, sep=";", encoding="utf-8")

    return out


if __name__ == "__main__":
    df = build_process_capacity_template_from_processes()
    print(df.to_string(index=False))
    print("BASE_DIR:", BASE_DIR)
    print("saved:", DATA_SCHEMAS_DIR / "process_capacity_template.csv")
