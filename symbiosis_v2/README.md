# symbiosis_v2

OSB ölçeğinde endüstriyel simbiyoz için **LCA + skor + GAMS** çekirdeği.

- Mimari: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Aylık girdi/çıktı: [`data_runtime/README.md`](data_runtime/README.md)

## Kurulum

```bash
cd symbiosis_v2
pip install -r requirements.txt
```



## Aylık pipeline

`data_runtime/` içine zorunlu Excel/CSV dosyalarını koyun (bkz. `data_runtime/README.md`).

Çalışma dizini `symbiosis_v2` olmalı; modüller kökü `sys.path` ile ekler.

## Senaryo

Önce üretim çıktısı `matches_LCA_{YYYY-MM}.xlsx` ve `process_capacity_monthly_{YYYY-MM}.xlsx` oluşmuş olmalı.

```python
from pathlib import Path
from pipeline.scenario import ScenarioWasteBounds, run_scenario_pipeline

run_scenario_pipeline(1, "2026-05", waste_bounds=ScenarioWasteBounds(global_max_kg_month=1e6))
```

## Yapılandırma

| Ortam | Anlamı |
|--------|--------|
| `LCA_API_URL` / `LCA_SERVICE_URL` | LCA mikroservis tabanı |
| `GAMS_EXE` | `gams.exe` tam yolu |
| `USE_MOCK_LCA` | `1` → HTTP yerine mock LCA |

Kod içi sabitler: `core.config` → `BASE_DIR`, `RUNTIME_DIR` (`data_runtime`), `DATA_SCHEMAS_DIR`.
