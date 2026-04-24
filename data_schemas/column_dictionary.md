# Veri sözlüğü — teknofest_arastirma

Kolon adları **Python pipeline** (`generate_monthly_data_3step` ile uyumlu), **GAMS GDX** (`gams_doc._build_and_write_gdx`) ve **ORM** (`webapp/models`) ile aynı isimlendirme düzenini hedefler.

**Tipler:** `string`, `int`, `float`, `bool` (Excel’de 0/1), `month_1_12` (1–12 arası takvim ayı).

---

## 1. factories (`factories_template.xlsx`)

OSB’deki tesisler; mesafe ve harita için koordinat.

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `id` | Evet | int | Birincil anahtar; fabrika kimliği | — |
| `name` | Evet | string | Tesis adı | — |
| `lat` | Evet | float | Enlem (WGS84) | — |
| `lng` | Evet | float | Boylam (WGS84) | — |

**Örnek satır:** `101 | "Kimya A.Ş." | 40.12 | 29.05`

---

## 2. processes (`processes_template.xlsx`)

Üretim / geri kazanım prosesleri; hedef tarafta kapasite kısıtına bağlanır.

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `process_id` | Evet | string | Birincil anahtar | — |
| `factory_id` | Evet | int | Prosesin bağlı olduğu tesis | → `factories.id` |
| `process_name` | Evet | string | Görünen ad | — |
| `nace_code` | Hayır | string | NACE sınıflaması (raporlama) | — |
| `accepted_physical_states` | Hayır | string | Ön-elemede Filtre 2: kabul edilen formlar (`solid`, `liquid`, `sludge`, `gas`; virgülle veya `all`) | — |
| `operation_mode` | Hayır | string | Ön-elemede Filtre 3: `batch` veya `continuous` (kaynak/hedef eşleşmesi) | — |
| `is_auxiliary_process` | Evet | int (0/1) | 1 ise yardımcı ünite: **eşleşme üretimi ve kapasite toplamına dahil edilmez** (`pipeline.monthly`) | — |

**Örnek satır:** `"P-12" | 101 | "Solvent geri kazanımı" | "20.13" | 0`

---

## 3. waste_streams (`waste_streams_template.xlsx`)

Atık tanımı; LCA’de taşıma modu (`physical_state`) ve isteğe bağlı bertaraf maliyeti için kullanılır.

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `waste_id` | Evet | string | Birincil anahtar | — |
| `process_id` | Evet | string | Atığı üreten proses | → `processes.process_id` |
| `ewc_code` | Evet | string | Avrupa Atık Kodu | — |
| `physical_state` | Evet | string | Örn. sıvı/katı; taşıma modu seçiminde kullanılır (`sıvı` → tanker) | — |
| `disposal_cost_per_ton` | Hayır | float | Bertaraf maliyeti (ekonomik LCA; varsayılan servis içinde) | — |
| `is_hazardous` | Hayır | int (0/1) | Ön-eleme F5: tehlikeli atık işaretleri (yoksa EWC’den sezgisel) | — |

**Örnek satır:** `"W-01" | "P-12" | "06 01 04" | "sıvı" | 50.0`

---

## 3b. ewc_nace_map (`ewc_nace_map.csv` / `.xlsx`, `outputs/runtime/`)

Ön-eleme Filtre 1 (EWC → izin verilen NACE listesi). Çok satır: aynı `ewc_code` birden çok `nace_code` ile.

| Kolon | Zorunlu | Tip | Açıklama |
|-------|---------|-----|----------|
| `ewc_code` | Evet | string | Avrupa Atık Kodu (`waste_streams.ewc_code` ile hizalı) |
| `nace_code` | Evet | string | Uyumlu NACE (ör. `20.13`) |

Şablon: `data_schemas/templates/ewc_nace_map_template.csv`.

---

## 4. waste_coefficients (`waste_coefficients_template.xlsx`)

Atık bazlı geri kazanım / hedef kaynak bilgisi; LCA servisindeki `waste_recovery` ile aynı rol (legacy uyumu). Aylık akış için isteğe bağlı **kg** sınırları ve meta alanlar.

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `waste_id` | Evet | string | Atık kimliği | → `waste_streams.waste_id` |
| `recovery_rate` | Evet | float | 0–1 arası kütlesel geri kazanım oranı | — |
| `target_resource_type` | Evet | string | Önlenen virgin kaynak türü; `resource_emission.resource_type` ile eşleşmeli | → `resource_emission.resource_type` (mantıksal) |
| `kg_per_ton_min` | Hayır | float | `waste_amount_monthly` (kg) için alt sınır; her ikisi doluysa kırpma (`pipeline.monthly.apply_waste_kg_min_max`) | — |
| `kg_per_ton_max` | Hayır | float | Üst sınır (kg/ay) | — |
| `recovery_method` | Hayır | string | Geri kazanım yöntemi (raporlama) | — |
| `potential_industrial_symbiosis` | Hayır | string veya 0/1 | Simbiyoz potansiyeli işareti | — |
| `notes` | Hayır | string | Serbest not | — |

**Örnek satır:** `"W-01" | 0.82 | "plastic_PE" | 1000.0 | 50000.0 | "mechanical" | 1 | "pilot"`

---

## 4b. process_metadata (`process_metadata.xlsx`)

Proses başına BREF kaynak tüketimi / verim **aralıkları** ve referans metni; skor katmanına girdi (`placeholder_process_metadata_for_scoring`).

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `process_id` | Evet | string | Proses | → `processes.process_id` |
| `water_min` | Hayır | float | Su kullanımı alt sınırı (birim: operasyonel tanım) | — |
| `water_max` | Hayır | float | Üst sınır | — |
| `energy_min` | Hayır | float | Enerji alt sınırı | — |
| `energy_max` | Hayır | float | Üst sınır | — |
| `electricity_min` | Hayır | float | Elektrik alt sınırı | — |
| `electricity_max` | Hayır | float | Üst sınır | — |
| `chemicals_min` | Hayır | float | Kimyasal kullanım alt sınırı | — |
| `chemicals_max` | Hayır | float | Üst sınır | — |
| `yield_min` | Hayır | float | Verim / çıktı oranı alt sınırı | — |
| `yield_max` | Hayır | float | Üst sınır | — |
| `bref` | Hayır | string | BREF veya kaynak doküman özeti | — |

**Örnek satır:** `"P-12" | 1.0 | 5.0 | 10.0 | 80.0 | 50.0 | 400.0 | 0.1 | 2.0 | 0.7 | 0.95 | "BREF Common Waste Water 2022"` 

---

## 4c. bref_emission_limits (`bref_emission_limits.xlsx`)

Proses + emisyon parametresi bazlı limitler; **senaryo raporlaması** (`pipeline.scenario.emission_limits_report`).

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `process_id` | Evet | string | Proses | → `processes.process_id` |
| `parameter` | Evet | string | Örn. `NOx`, `dust`, `COD` | — |
| `min` | Hayır | float | İzin alt sınırı | — |
| `max` | Hayır | float | Üst sınır | — |
| `unit` | Evet | string | Ölçü birimi | — |
| `bref_reference` | Hayır | string | Kaynak atıfı | — |

**Örnek satır:** `"P-12" | "NOx" | 0.0 | 150.0 | "mg/Nm3" | "BREF Large Combustion Plants"`

---

## 5. capacity_factors (`capacity_factors_template.xlsx`)

Fabrika bazlı aylık kapasite çarpanı (`generate_monthly_data` içindeki `get_capacity_factor`).

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `factory_id` | Evet | int | Tesis | → `factories.id` |
| `month` | Evet | month_1_12 | Takvim ayı (1–12) | — |
| `capacity_factor` | Evet | float | Çarpan (örn. 0.9 sezon düşüşü) | — |

**Örnek satır:** `101 | 5 | 1.0`

---

## 6. resource_use (`resource_use_template.xlsx`)

Kaynak birim ekonomisi; LCA `calculator` içinde `cost_per_unit` sözlüğü.

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `resource_type` | Evet | string | Kaynak türü anahtarı | → `waste_coefficients.target_resource_type` (mantıksal) |
| `cost_per_unit` | Evet | float | Birim başına maliyet (model para birimi) | — |

**Örnek satır:** `"plastic_PE" | 0.5`

---

## 7. resource_emission (`resource_emission_template.xlsx`)

Virgin kaynak emisyon faktörleri; LCA `LEGACY_EMISSIONS` ile uyumlu.

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `resource_type` | Evet | string | Kaynak türü anahtarı | → `waste_coefficients.target_resource_type` (mantıksal) |
| `emission_factor_kg_co2_per_unit` | Evet | float | Birim başına kg CO₂e | — |
| `unit` | Evet | string | Faktörün fiziksel birimi (örn. `kg_material`) | — |

**Örnek satır:** `"plastic_PE" | 2.1 | "kg_material"`

---

## 7a. waste_process_links (`waste_process_links.xlsx`) — otomatik veya elle

**Otomatik:** `core.waste_process_links_generator` — her `waste_id` için tüm (yardımcı olmayan) hedef proseslerle kartesyen satırlar; `python -m core.waste_process_links_generator` veya aylık pipeline başı.

| Kolon | Zorunlu (otomatik) | Tip | Açıklama |
|-------|-------------------|-----|----------|
| `waste_id` | Evet | string | → `waste_streams.waste_id` |
| `source_process_id` | Evet | string | Atığı üreten proses → `waste_streams.process_id` |
| `source_factory_id` | Evet | int | Kaynak fabrika → `processes.factory_id` |
| `target_process_id` | Evet | string | Hedef proses (yardımcı olamaz) |
| `target_factory_id` | Evet | int | Hedef fabrika |
| `waste_amount_base` | Evet | float | kg/ay; `waste_streams.waste_amount_base` varsa, yoksa 0 |
| `distance_km` | Evet | float | Haversine (fabrika koordinatları) |
| `transport_mode` | Evet | string | `liquid`→tanker, `solid`→truck, `gas`→pipeline, diğer→truck (LCA’ye normalize) |
| `match_id` | Evet | int | 0,1,2,… benzersiz |

**İsteğe bağlı girdi:** `process_capacity_monthly_YYYY-MM.xlsx` (yalnızca bilgi amaçlı log; üretim formülünde kullanılmaz).

**Eski minimal şema** (yalnızca `waste_id`, `target_process_id` / `process_id`, `waste_amount_base`): `matches_ready_builder` eski yolu kullanır; mesafe yeniden hesaplanır.

**Elle düzenleme:** `SYMBIOSIS_SKIP_WASTE_LINKS_AUTOGEN=1` ile pipeline başındaki otomatik üretimi kapatın.

---

## 8. matches_ready (`matches_ready_template.xlsx`)

**Girdi şablonu:** Eski projedeki `matches_LCA_ready.xlsx` ile aynı rol. Bu dosya doldurulduktan sonra aylık üretim; çıktı **`matches_LCA_{YYYY-MM}.xlsx`** olur ve **GAMS’e giden** tablo budur (LCA + skor sonrası).

### 8a. Kullanıcının doldurduğu zorunlu kolonlar (şablonda yer alır)

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `waste_id` | Evet | string | Atık | → `waste_streams.waste_id` |
| `process_id` | Evet | string | Hedef proses | → `processes.process_id` |
| `source_factory` | Evet | int | Atığın çıktığı tesis | → `factories.id` |
| `target_factory` | Evet | int | İşlemin yapıldığı tesis (kapasite birleştirmesi için) | → `factories.id` |
| `waste_amount_base` | Evet | float | Aylık baz atık miktarı **kg** (çarpanlardan önce) | — |
| `distance_km` | Evet | float | Kaynak–hedef mesafe (km); LCA taşıma | — |

### 8b. İsteğe bağlı girdi (şablonda yer alır)

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `tech_score` | Hayır | float | 0–1 teknik uygunluk; boşsa skor adımında varsayılan kullanılır | — |
| `match_id` | Hayır | string | Sabit kimlik; boşsa satır indeksi ile üretilir | — |

### 8c. `matches_LCA_{YYYY-MM}.xlsx` dosyasında pipeline’ın ürettiği (GAMS / temizlik için gerekli; şablonda kullanıcı doldurmaz)

| Kolon | Kaynak | Tip | Açıklama | GAMS |
|-------|--------|-----|----------|------|
| `physical_state` | `waste_streams` birleşimi | string | Taşıma modu | LCA isteği |
| `waste_amount_monthly` | Hesaplanan kg/ay | float | Çarpanlı aylık miktar; `waste_coefficients.kg_per_ton_min/max` ile kırpılabilir | `W(m)` |
| `net_co2e` | LCA servisi | float | Net CO₂e **tCO₂e** (LCA API `net_co2e`) | `env_score` girdisi |
| `profit` | LCA servisi | float | Ekonomik net | `economic_score` |
| `env_score` | Skor adımı | float | 0–1 | `E(m)` |
| `economic_score` | Skor adımı | float | 0–1 | — |
| `sustainability_score` | Skor adımı | float | 0–1 bileşik | `S(m)` |
| `match_id` | İndeks veya girdi | string | GDX `m` | `m` |
| LCA detay sütunları | LCA servisi | float | Örn. `transport_emissions`, `processing_emissions`, `avoided_emissions`, `recovered_mass_monthly`, `transport_cost` | — |

**GAMS doğrudan kullanan kolonlar:** `match_id`, `waste_id`, `process_id`, `sustainability_score` (`S`), `env_score` (`E`), `waste_amount_monthly` (`W`).

**Örnek girdi satırı (şablon):** `"W-01" | "P-12" | 101 | 102 | 15000.0 | 45.2 | 0.85`

---

## 9. factory_status (`factory_status_template.xlsx`)

Aylık fabrika durum çarpanı (`generate_monthly_data` içinde `f_status`).

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `factory_id` | Evet | int | Tesis | → `factories.id` |
| `month` | Evet | month_1_12 | Takvim ayı | — |
| `status` | Evet | float | 0–1 arası üretim/durum çarpanı | — |

**Örnek satır:** `101 | 5 | 1.0`

---

## 10. process_status (`process_status_template.xlsx`)

Aylık proses durum çarpanı (`p_status`).

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `process_id` | Evet | string | Proses | → `processes.process_id` |
| `month` | Evet | month_1_12 | Takvim ayı | — |
| `status` | Evet | float | 0–1 arası çarpan | — |

**Örnek satır:** `"P-12" | 5 | 1.0`

---

## 11. process_capacity (`process_capacity_template.csv`)

Proses günlük kapasitesi (ton/gün); `process_capacity.csv` ile uyumlu. Aylık kg kapasite **pipeline içinde** türetilir.

| Kolon | Zorunlu | Tip | Açıklama | İlişki |
|-------|---------|-----|----------|--------|
| `process_id` | Evet | string | Proses | → `processes.process_id` |
| `capacity_ton_per_day` | Evet | float | Ton/gün (ondalık ayırıcı: nokta veya yerel ayarda virgül) | — |

**Örnek satır:** `"P-12",12.5`

---

## Özet ilişki grafiği (metin)

```
factories.id ← processes.factory_id
factories.id ← factory_status.factory_id
factories.id ← capacity_factors.factory_id
factories.id ← matches_ready.source_factory
factories.id ← matches_ready.target_factory

processes.process_id ← waste_streams.process_id
processes.process_id ← process_status.process_id
processes.process_id ← process_capacity.process_id
processes.process_id ← matches_ready.process_id
processes.process_id ← process_metadata.process_id
processes.process_id ← bref_emission_limits.process_id

waste_streams.waste_id ← waste_coefficients.waste_id
waste_streams.waste_id ← matches_ready.waste_id

waste_coefficients.target_resource_type ↔ resource_emission.resource_type
waste_coefficients.target_resource_type ↔ resource_use.resource_type
```

---

## Notlar

- `matches_ready` şablonu **yalnızca girdi** kolonlarını içerir; `matches_LCA_*` çıktısındaki LCA ve skor kolonları bu dosyaya manuel yazılmaz.
- `process_capacity` kök dizinde CSV olarak okunur (`sep=';'` ve `decimal=','` eski script ile uyumlu); şablon dosya adı ve sütunlar aynı sözleşmeyi taşır.
- LCA mikroservisi ayrı SQLite kullanır (`ProcessLCAProfile`, `EmissionFactor`); `resource_*` şablonları kök Excel’lerden legacy yükleme ile hizalıdır.
- **Senaryo:** `ScenarioWasteBounds` ile `waste_amount_monthly` üzerinde ek min–max (global veya `waste_id` bazlı); `bref_emission_limits` satırları `emission_limits_report` çıktısında listelenir.
- **Yardımcı proses:** `is_auxiliary_process=1` satırları eşleşme ve kapasite türetiminden çıkarılır (`pipeline.monthly`).
