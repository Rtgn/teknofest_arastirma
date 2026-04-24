"""
matches + kapasite DataFrame'lerinden GAMS girişi: CSV dosyaları.
matches.gdx üretimi build_gdx.gms + csv2gdx ile GAMS tarafında yapılır (Python API yok).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from optimization.result_reader import normalize_match_id

# build_gdx.gms ile uyumlu dosya adları (çalışma dizininde)
GAMS_CSV_S = "gams_S.csv"
GAMS_CSV_E = "gams_E.csv"
GAMS_CSV_W = "gams_W.csv"
GAMS_CSV_IW = "gams_IW.csv"
GAMS_CSV_JP = "gams_JP.csv"
GAMS_CSV_CAP = "gams_Cap.csv"


def _write_gams_csv_inputs(
    df: pd.DataFrame,
    cap_df: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """GAMS build_gdx.gms / csv2gdx için CSV'leri yazar. Beklenen matches.gdx yolunu döner."""
    df = df.copy()
    df = df.assign(match_id=df["match_id"].map(normalize_match_id))
    df = df[df["match_id"] != ""]

    one_per_m = df.drop_duplicates(subset=["match_id"], keep="last")
    env_col = "env_score" if "env_score" in df.columns else "sustainability_score"

    cap_df = cap_df.copy().assign(process_id=cap_df["process_id"].astype(str))
    cap_map = dict(zip(cap_df["process_id"], cap_df["capacity_monthly"]))
    BIG_CAP = 1e12

    j_list = df["process_id"].astype(str).unique().tolist()

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    s_df = one_per_m[["match_id", "sustainability_score"]].copy()
    s_df.columns = ["match_id", "S"]
    s_df.to_csv(output_dir / GAMS_CSV_S, index=False)

    e_df = one_per_m[["match_id", env_col]].copy()
    e_df.columns = ["match_id", "E"]
    e_df.to_csv(output_dir / GAMS_CSV_E, index=False)

    w_df = one_per_m[["match_id", "waste_amount_monthly"]].copy()
    w_df.columns = ["match_id", "W"]
    w_df.to_csv(output_dir / GAMS_CSV_W, index=False)

    iw_df = df[["match_id", "waste_id"]].copy()
    iw_df["waste_id"] = iw_df["waste_id"].astype(str)
    iw_df["val"] = 1.0
    iw_df.to_csv(output_dir / GAMS_CSV_IW, index=False)

    jp_df = df[["match_id", "process_id"]].copy()
    jp_df["process_id"] = jp_df["process_id"].astype(str)
    jp_df["val"] = 1.0
    jp_df.to_csv(output_dir / GAMS_CSV_JP, index=False)

    cap_rows = []
    for j_el in j_list:
        cap_rows.append(
            {"process_id": j_el, "Cap": float(cap_map[j_el]) if j_el in cap_map else BIG_CAP}
        )
    pd.DataFrame(cap_rows).to_csv(output_dir / GAMS_CSV_CAP, index=False)

    return output_dir / "matches.gdx"


def build_gdx_from_frames(
    matches_df: pd.DataFrame,
    capacity_df: pd.DataFrame,
    output_dir: Path,
    *,
    label: str = "",
    gdx_name: str = "matches.gdx",
) -> Path:
    """
    DataFrame'lerden GAMS giriş CSV'lerini yazar. matches.gdx, build_gdx.gms çalıştırıldığında üretilir.
    Dönüş: beklenen matches.gdx yolu (gdx_name şu an yalnızca uyumluluk için; dosya adı matches.gdx).
    """
    del label, gdx_name  # uyumluluk; CSV akışında kullanılmıyor
    df = matches_df.copy()
    if "match_id" not in df.columns:
        df["match_id"] = [normalize_match_id(i) for i in df.index]
    cap = capacity_df.copy().assign(process_id=capacity_df["process_id"].astype(str))
    _write_gams_csv_inputs(df, cap, output_dir)
    return (output_dir / "matches.gdx").resolve()


def build_gdx_from_excel_paths(
    matches_xlsx: Path,
    cap_xlsx: Path,
    output_dir: Path,
    *,
    label: str = "",
) -> Path:
    del label
    df = pd.read_excel(matches_xlsx)
    df["match_id"] = [normalize_match_id(i) for i in df.index]
    cap_df = pd.read_excel(cap_xlsx)
    cap_df = cap_df.assign(process_id=cap_df["process_id"].astype(str))
    _write_gams_csv_inputs(df, cap_df, output_dir)
    return (output_dir / "matches.gdx").resolve()
