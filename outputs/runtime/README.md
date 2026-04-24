# outputs/runtime — aylık girdi ve çıktı

Aylık pipeline (`pipeline.monthly.run_monthly_pipeline`) bu dizini okur ve üretilen dosyaları buraya yazar.

## Zorunlu girdi dosyaları

| Dosya | Açıklama |
|-------|----------|
| `factories.csv` | `id`, `lat`, `lng` |
| `processes.csv` | `process_id`, `factory_id`, isteğe bağlı `is_auxiliary_process` |
| `waste_streams.csv` | `waste_id`, `process_id` (atığı **üreten** proses), `physical_state`, … |
| `waste_process_links.csv` | `waste_id`, `target_process_id` (veya `process_id` = hedef proses), `waste_amount_base` (kg/ay); isteğe bağlı `tech_score`, `match_id` |
| `capacity_factors.csv` | `factory_id`, `month`, `capacity_factor` |
| `factory_status.csv` | `factory_id`, `month`, `status` |
| `process_status.csv` | `process_id`, `month`, `status` |
| `process_capacity.csv` | `process_id`, `capacity_ton_per_day` (`;` ayırıcı) |
| `process_metadata.csv` | Proses başına BREF kaynak aralıkları (skor birleştirme girdisi) |

## Ön eşleşme (`matches_LCA_ready.csv`) — otomatik üretim

Yukarıdaki **dört temel dosya** (`factories`, `processes`, `waste_streams`, `waste_process_links`) birlikte mevcut olduğunda pipeline başında `matches_LCA_ready.csv` otomatik üretilir. Mesafe `distance_km` kaynak ve hedef fabrika koordinatlarından (Haversine) hesaplanır.

Bu dörtlü **yoksa** ve `matches_LCA_ready.csv` el ile konmuşsa o dosya kullanılır. İkisini de sağlamak mümkün değilse hata verilir.

Elle düzenlenmiş `waste_process_links.csv` dosyasını korumak için: `SYMBIOSIS_SKIP_WASTE_LINKS_AUTOGEN=1`.

**Zorunlu symbiosis modu:** `SYMBIOSIS_STRICT_MATCHES=1` veya `run_monthly_pipeline(..., strict_symbiosis_matches=True)` — dört dosya olmadan çalışmaz (yalnızca otomatik üretim).

Komut satırı: `python -m core.waste_process_links_generator --runtime outputs/runtime --period 2026-01`

## İsteğe bağlı girdiler

- `waste_coefficients.csv` — aylık atık kg min/max kırpımı (yoksa kırpılmaz)
- `bref_emission_limits.csv` — senaryo BREF emisyon limit raporu (yoksa boş rapor üretilir)

## Çıktılar (örnek periyot `2026-05`)

- `matches_LCA_2026-05.csv`, `process_capacity_monthly_2026-05.csv`
- `osb_limit.txt`, `selected_matches.csv` (PuLP+CBC MILP çözücüsü)
- `selected_raw_2026-05.csv`, `selected_matches_2026-05.csv`
- Senaryolar için: `scenario_runs/{scenario_id}/` alt dizini + köke kopyalanan `matches_LCA_{YYYY-MM}__SIM{id}.csv`, `selected_matches_{YYYY-MM}__SIM{id}.csv`

LCA testi için: `USE_MOCK_LCA=1` ortam değişkeni (gerçek HTTP yerine mock).
