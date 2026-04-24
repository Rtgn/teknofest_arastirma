# teknofest_arastirma — Mimari Özeti

Bu belge, OSB ölçeğinde **endüstriyel simbiyoz** karar destek sisteminin v2 çekirdeğini anlatır: LCA tabanlı çevresel/ekonomik metrikler, bileşik skorlar ve **GAMS** ile binary seçim optimizasyonu. Eski `tk_arastirma` deposundaki bilimsel hedef korunur; kod ve veri düzeni sadeleştirilir.

---

## 1. Tasarım ilkeleri

- **Tek sorumluluk:** `core` (iş kuralları ve dış servis sözleşmeleri), `optimization` (GDX/GAMS/sonuç okuma), `pipeline` (üretim ve senaryo orkestrasyonu), `data_schemas` (şablon ve sütun sözleşmesi), `app` (Flask arayüzü + HTTP uçları), `services` (LCA ve raporlama), `utils` (yardımcı betikler).
- **Periyot:** Tüm üretim çıktıları `YYYY-MM` ile etiketlenir; senaryo koşuları ayrı bir sanal periyot veya etiket ile izole edilir (v1 ile uyumlu düşünülmüştür).
- **Girdi/çıktı ayrımı:** Ham Excel/CSV şablonları `data_schemas/templates/` altında; çalışma sırasında üretilen aylık dosyalar `outputs/runtime/` altında tutulur.

---

## 2. Ana modüller

| Modül | Klasör | Görev |
|-------|--------|--------|
| **Yapılandırma ve periyot** | `core/` | Periyot parse/format, yol politikası, ortam değişkenleri (LCA URL, GAMS exe). |
| **Veri temizliği** | `core/data_cleaning.py` | Tekrar satırlar, winsorization, sayısal zorlama (v1 `data_cleaner` ile aynı rol). |
| **Skor** | `core/scoring.py` | LCA çıktılarından sürdürülebilirlik / env / econ / tech bileşimi. |
| **LCA istemcisi** | `core/lca_client.py` | HTTP batch çağrısı (`/calculate_lca/batch`); sonuçları DataFrame’e işleme. |
| **GAMS giriş CSV** | `optimization/gdx_builder.py` | Eşleşme + kapasite tablolarından `gams_*.csv`; `matches.gdx` yalnızca GAMS’ta (`build_gdx.gms` + `csv2gdx`). |
| **GAMS çalıştırma** | `optimization/gams_runner.py` | Yalnızca `subprocess` ile `gams.exe` (`build_gdx.gms` sonra `new3.gms`). |
| **Sonuç okuma** | `optimization/result_reader.py` | `selected_matches.csv` (`match_id`, `level`) → eşik sonrası `match_id` listesi. |
| **Aylık pipeline** | `pipeline/monthly.py` | LCA öncesi üretim → (opsiyonel) `waste_coefficients` ile **kg min–max** → yardımcı prosesleri eleme → `process_metadata` skor yer tutucusu → temizlik → GAMS → seçilen sonuçlar (`run_monthly_pipeline` uçtan uca sonra). |
| **Senaryo pipeline** | `pipeline/scenario.py` | `ScenarioWasteBounds` ile senaryo **atık kg min–max** → `emission_limits_report` ile **BREF limit** raporu → modifikasyon / LCA / GAMS (`run_scenario_pipeline` uçtan uca sonra). |
| **Uygulama** | `app/` | Tek Flask uygulaması: UI, pipeline API’leri ve yerel LCA route’ları. |
| **Servisler** | `services/` | Dahili LCA ve raporlama modülleri. |
| **Yardımcılar** | `utils/` | Tek seferlik yardımcı betikler ve şablon üreticiler. |

---

## 3. Veri akışı (genel)

```
Şablon + referans Excel/CSV
        ↓
  Yardımcı prosesleri ele (is_auxiliary_process) + atık kg min–max (waste_coefficients)
        ↓
  (Aylık üretim: kapasite/atık birleşimi — core modülleri; process_metadata skor yer tutucusu)
        ↓
Yerel LCA API (`/api/lca/...`) → net CO₂, kâr, taşıma vb.
        ↓
Skor birleştirme (ağırlıklar) + veri temizliği
        ↓
GAMS giriş CSV + osb_limit.txt + build_gdx.gms → matches.gdx + new3.gms
        ↓
GAMS → selected_matches.csv
        ↓
Seçilen eşleşmeler + raporlama (Excel/DB — sonraki aşama)
```

**Not:** LCA için hafif SQLite kullanılır; ana uygulama verisi yine Excel/CSV runtime dosyalarındadır.

---

## 4. Aylık pipeline

1. **Girdi:** Referans tablolar (`factories`, `processes`, `waste_streams`, `capacity_factors`, `matches_ready`, `waste_coefficients`, `process_metadata`, `bref_emission_limits` vb.) + isteğe bağlı durum dosyaları (`factory_status`, `process_status`, `process_capacity` CSV).
2. **Proses sınıflandırma:** `processes.is_auxiliary_process = 1` olan `process_id` değerleri **eşleşme adayları** ve **process_capacity** toplamlarından çıkarılır (`filter_auxiliary_from_*`, `auxiliary_process_ids`).
3. **Atık miktarı:** `waste_amount_base` → `waste_amount_monthly` (kg/ay); `waste_coefficients.kg_per_ton_min` / `kg_per_ton_max` doluysa aylık akışa **mutlak kg sınırı** olarak kırpma uygulanır (`compute_waste_amount_monthly_column`, `apply_waste_kg_min_max`).
4. **Skor yer tutucu:** `process_metadata` ile `process_id` birleştirilir; BREF aralıklarından türetilecek ceza/ödül sütunları için `placeholder_process_metadata_for_scoring` (şimdilik 0; gerçek formül `core/scoring.py`).
5. **Türetim:** `matches_LCA_{YYYY-MM}.xlsx`, `process_capacity_monthly_{YYYY-MM}.xlsx`, `osb_limit.txt`.
6. **LCA:** `core/lca_client.py` batch.
7. **Temizlik:** `core/data_cleaning.py`.
8. **Optimizasyon:** `optimization/gdx_builder.py` → `gams_runner.py` → `result_reader.py`.
9. **Çıktı:** Seçilen satırlar; durum katmanı ileride `app` veya ayrı bir kalıcı katmana taşınabilir.

---

## 5. Senaryo pipeline

1. **Baz:** Belirli bir `YYYY-MM` için üretilmiş `matches_LCA_*` ve `process_capacity_monthly_*` (dosya veya bellek).
2. **Atık min–max (senaryo):** `ScenarioWasteBounds` — global ve/veya `waste_id` başına `min`/`max` kg/ay; `apply_scenario_waste_bounds` ile `waste_amount_monthly` güncellenir (üretimdeki kırpmadan ayrı veya üzerine senaryo katmanı).
3. **Emisyon limitleri raporu:** `bref_emission_limits.xlsx` (veya DataFrame) `emission_limits_report` ile senaryo çıktısına eklenir (`limits`, `scenario_id`, `base_period`).
4. **Modifikasyon:** Atık çarpanı, kapasite çarpanı, satır eleme, LCA yeniden koşumu (v1 ile aynı fikir).
5. **Skor + temizlik:** Üretim ile aynı fonksiyonlar; ağırlıklar senaryoya göre değişebilir.
6. **GAMS:** Ayrı çalışma dizini (`scenario_runs/{id}/` benzeri).
7. **Çıktı:** Senaryo etiketi ile ayrılmış sonuçlar + rapor sözlüğünde emisyon limitleri özeti.

---

## 6. GAMS entegrasyonu

- **Model dosyası:** `optimization/gms/README.md` — `new3.gms` buraya veya yapılandırılan yola konur (bu repoda şimdilik kopyalanmaz).
- **Ara dosyalar:** `gams_*.csv` (Python), `matches.gdx` (`csv2gdx`), `osb_limit.txt`, `selected_matches.csv` (GAMS `Put`, binary `x` için `level`).
- **Python:** `import gams` yok; yalnızca CSV yazma/okuma ve `gams.exe` çağrısı.
- **Ortam:** `GAMS_EXE` veya `PATH` üzerinden `gams.exe` (`resolve_gams_executable`).

---

## 7. Excel şablonlarının rolleri (`data_schemas/templates/`)

| Şablon | Rol |
|--------|-----|
| `factories_template.xlsx` | Fabrika kimliği, ad, koordinat (harita/mesafe). |
| `processes_template.xlsx` | Proses–fabrika bağlantısı, NACE vb. |
| `waste_streams_template.xlsx` | Atık kimliği, EWC, proses bağlantısı, fiziksel hal (taşıma modu). |
| `waste_coefficients_template.xlsx` | Atık/proses dönüşüm veya kullanım katsayıları (iş kuralına göre). |
| `capacity_factors_template.xlsx` | Aylık kapasite çarpanları / üst sınırlar. |
| `resource_use_template.xlsx` | Birim başına kaynak kullanımı (LCA profiline girdi olabilir). |
| `resource_emission_template.xlsx` | Emisyon/kaynak faktörleri (servis veya yerel tablo). |
| `matches_ready_template.xlsx` | Ham veya ön eşleşme adayları (kaynak/hedef, mesafe, miktar). |
| `factory_status_template.xlsx` | Dönemsel fabrika durumu (isteğe bağlı). |
| `process_status_template.xlsx` | Dönemsel proses durumu (isteğe bağlı). |
| `process_capacity_template.csv` | CSV alternatifi; toplu kapasite serisi. |
| `process_metadata.xlsx` | Proses başına BREF kaynak aralıkları (su, enerji, elektrik, kimyasal, verim) ve BREF referans metni; skor katmanı için girdi. |
| `bref_emission_limits.xlsx` | Proses + parametre bazlı emisyon limitleri (min/max, birim, BREF referansı); senaryo raporlaması ve uyum özetleri. |

**Kolon ekleri (mevcut şablonlar):**

- `processes_template.xlsx`: `is_auxiliary_process` (0/1) — yardımcı proses; kapasite ve eşleşme üretiminde hariç tutulur.
- `waste_coefficients_template.xlsx`: `kg_per_ton_min`, `kg_per_ton_max` (aylık kg kırpımı için), `recovery_method`, `potential_industrial_symbiosis`, `notes`.

Çalışma anında üretilen dosya adları (v1 ile uyum): `matches_LCA_{YYYY-MM}.xlsx`, `process_capacity_monthly_{YYYY-MM}.xlsx`, `selected_matches_{YYYY-MM}.xlsx` — bunlar şablon değil **çıktı** kabul edilir ve `outputs/runtime/` altında tutulur.

---

## 8. Klasör ağacı (özet)

```
teknofest_arastirma/
├── core/
├── app/
├── services/
│   ├── lca/
│   └── reporter/
├── optimization/
│   └── gms/          # README: .gms dosyası konumu
├── pipeline/
├── utils/
├── outputs/
│   └── runtime/
├── data_schemas/
│   └── templates/    # Excel/CSV şablonları
└── docs/
    └── ARCHITECTURE.md
```

---

## 9. Sonraki adımlar (kod doldurma sırası)

1. `core.period` + yapılandırma (BASE_DIR, LCA URL).
2. LCA istemcisi ve skor fonksiyonları (v1 ile sütun uyumu).
3. GDX builder + result reader (v1 `gams_doc` / `match_ids` ile parity).
4. `pipeline/monthly` tek uçtan çağrılabilir API.
5. Senaryo modifikasyon sözleşmesi ve `pipeline/scenario`.
6. `web` blueprint’leri ve kalıcı katman (opsiyonel).

*Belge, v2 iskelet oluşturma aşamasında yazılmıştır; dosya yolları implementasyonla netleştirilecektir.*
