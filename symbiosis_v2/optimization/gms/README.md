# GAMS model dosyaları

Bu dizine **`new3.gms`** (optimizasyon modeli) ve **`build_gdx.gms`** (CSV → `matches.gdx`, `csv2gdx`) konur.

Calisma aninda (or. `outputs/runtime/` veya senaryo calisma dizini) beklenenler:

- **Python’un yazdığı CSV:** `gams_S.csv`, `gams_E.csv`, `gams_W.csv`, `gams_IW.csv`, `gams_JP.csv`, `gams_Cap.csv` (`optimization/gdx_builder.py`)
- **`osb_limit.txt`**
- **`build_gdx.gms`** çalıştırılır → **`matches.gdx`**
- **`new3.gms`** çalıştırılır → **`selected_matches.csv`** (binary `x` için `match_id,level`)

Python tarafında GAMS Python API (`import gams`) kullanılmaz; yalnızca `gams.exe` ile `gams_runner.run_gams_model` çağrılır.
