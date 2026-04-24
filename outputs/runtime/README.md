# data_runtime — aylık girdi ve çıktı

Aylık pipeline (`pipeline.monthly.run_monthly_pipeline`) bu dizini okur ve üretilen dosyaları buraya yazar.

## `waste_process_links.xlsx` — otomatik üretim (pipeline ilk adım)

`factories.xlsx`, `processes.xlsx`, `waste_streams.xlsx` mevcutsa pipeline başında **`waste_process_links.xlsx`** üretilir veya güncellenir (kartesyen adaylar, mesafe, taşıma modu, `match_id`).

Elle düzenlenmiş dosyayı korumak için: `SYMBIOSIS_SKIP_WASTE_LINKS_AUTOGEN=1`.

Komut satırı: `python -m core.waste_process_links_generator --runtime data_runtime --period 2026-01`

## `matches_LCA_ready.xlsx` — otomatik üretim (önerilen)

Aşağıdaki **dört dosya** birlikte mevcut olduğunda pipeline başında `matches_LCA_ready.xlsx` **yeniden üretilir** (eski kök projeden kopyaya gerek yok):

| Dosya | Açıklama |
|-------|----------|
| `factories.xlsx` | `id`, `lat`, `lng` |
| `processes.xlsx` | `process_id`, `factory_id`, isteğe bağlı `is_auxiliary_process` |
| `waste_streams.xlsx` | `waste_id`, `process_id` (atığı **üreten** proses), `physical_state`, … |
| `waste_process_links.xlsx` | `waste_id`, `target_process_id` (veya `process_id` = hedef proses), `waste_amount_base` (kg/ay); isteğe bağlı `tech_score`, `match_id` |

Mesafe `distance_km` kaynak ve hedef fabrika koordinatlarından (Haversine) hesaplanır.

Bu dörtlü **yoksa** ve `matches_LCA_ready.xlsx` el ile konmuşsa o dosya kullanılır. İkisini de sağlamak mümkün değilse hata verilir.

**Zorunlu symbiosis modu:** ortam değişkeni `SYMBIOSIS_STRICT_MATCHES=1` veya `run_monthly_pipeline(..., strict_symbiosis_matches=True)` — dört dosya olmadan çalışmaz (yalnızca otomatik üretim).

## Zorunlu girdi dosyaları

| Dosya | Açıklama |
|-------|----------|
| `matches_LCA_ready.xlsx` | Ön eşleşme (`waste_amount_base`, `distance_km`, …) — yukarıdaki dörtlemeden de üretilebilir |
| `factory_status.xlsx` | `factory_id`, `month`, `status` |
| `process_status.xlsx` | `process_id`, `month`, `status` |
| `process_capacity.csv` | `process_id`, `capacity_ton_per_day` (`;` ayırıcı) |
| `waste_streams.xlsx` | En az `waste_id`, `physical_state` |
| `capacity_factors.xlsx` | `factory_id`, `month`, `capacity_factor` |

## Ön-eleme (waste_process_links otomatik üretimi)

Kartesyen aday sayısını düşürmek için `data_runtime/ewc_nace_map.csv` (veya `.xlsx`) kullanılır: `ewc_code`, `nace_code` sütunları. Şablon: `data_schemas/templates/ewc_nace_map_template.csv`.

`processes.xlsx` içinde isteğe bağlı: `accepted_physical_states` (ör. `solid,liquid,sludge,gas`), `operation_mode` (`batch` / `continuous`). `process_capacity.csv` ile debi/kapasite oranı süzülür.

## İsteğe bağlı

- `processes.xlsx` — otomatik `matches_LCA_ready` üretiminde zaten gerekli; ayrıca `is_auxiliary_process` ile yardımcı proses filtreleme
- `waste_coefficients.xlsx` — kg min/max kırpma
- `process_metadata.xlsx` — skor birleştirme (yer tutucu)

## Çıktılar (örnek periyot `2026-05`)

- `matches_LCA_2026-05.xlsx`, `process_capacity_monthly_2026-05.xlsx`
- `osb_limit.txt`, `selected_matches.csv` (PuLP+CBC MILP çözücüsü)
- `selected_raw_2026-05.xlsx`, `selected_matches_2026-05.xlsx`

LCA testi için: `USE_MOCK_LCA=1` ortam değişkeni (gerçek HTTP yerine mock).
