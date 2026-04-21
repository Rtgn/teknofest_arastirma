"""
data_runtime/waste_streams.xlsx içindeki tüm benzersiz ewc_code değerlerini listeler.

Kullanım (symbiosis_v2 dizininden):
  python scripts/list_unique_ewc_codes.py
  python scripts/list_unique_ewc_codes.py --runtime path/to/data_runtime
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parent.parent
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

import pandas as pd

from core.config import RUNTIME_DIR


def main() -> None:
    p = argparse.ArgumentParser(description="waste_streams benzersiz ewc_code")
    p.add_argument(
        "--runtime",
        type=Path,
        default=RUNTIME_DIR,
        help="data_runtime dizini",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="İsteğe bağlı: benzersiz kodları UTF-8 CSV olarak yaz (ewc_code)",
    )
    args = p.parse_args()
    runtime: Path = args.runtime
    ws_path = runtime / "waste_streams.xlsx"
    if not ws_path.is_file():
        print(f"Dosya yok: {ws_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_excel(ws_path, engine="openpyxl")
    col = "ewc_code"
    if col not in df.columns:
        print(f"'{col}' sütunu yok. Mevcut: {list(df.columns)}", file=sys.stderr)
        sys.exit(2)

    s = df[col].dropna().astype(str).str.strip()
    s = s[s != ""]
    unique = sorted(s.unique(), key=lambda x: (len(x), x))
    print(f"Kaynak: {ws_path}")
    print(f"Benzersiz ewc_code sayisi: {len(unique)}")
    print("---")
    for code in unique:
        print(code)

    if args.out:
        out = pd.DataFrame({"ewc_code": unique})
        args.out.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.out, index=False, encoding="utf-8-sig")
        print(f"---\nYazıldı: {args.out.resolve()}", file=sys.stderr)


if __name__ == "__main__":
    main()
