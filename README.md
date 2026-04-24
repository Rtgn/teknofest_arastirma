# teknofest_arastirma

Organize Sanayi Bölgeleri (OSB) için geliştirilmiş endüstriyel simbiyoz karar destek sistemi. Bu depo; veri hazırlama, YDA/LCA tabanlı çevresel ve ekonomik puanlama, optimizasyon ve Flask arayüzünü tek bir pakette birleştirir.

Bu proje hem teknik inceleyiciler hem de yarışma değerlendiricileri tarafından anlaşılabilir olacak şekilde düzenlenmiştir:

- Başlangıç noktası: [`docs/EVALUATOR_GUIDE.md`](docs/EVALUATOR_GUIDE.md)
- Teknik mimari: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Klasör haritası: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- Çalışma zamanı girdi/çıktı kuralları: [`outputs/runtime/README.md`](outputs/runtime/README.md)

## Sistem Ne Yapar

Sistem yüksek seviyede şunları yapar:

1. Excel/CSV dosyalarından fabrika, proses, atık ve kapasite verilerini okur.
2. Aylık endüstriyel simbiyoz eşleşme adayları üretir.
3. Önlenen emisyon, işleme yükü, taşıma yükü ve kâr gibi YDA/LCA tabanlı etki metriklerini hesaplar.
4. Eşleşme adaylarını puanlar.
5. En uygun ve uygulanabilir eşleşme kümesini seçmek için optimizasyon çalıştırır.
6. Akışı yerel Flask uygulaması ve yardımcı API'ler üzerinden sunar.

## Ana Klasörler

- [`app/`](app/README.md): Flask arayüzü ve HTTP uç noktaları
- [`core/`](core/README.md): ortak iş mantığı ve sözleşmeler
- [`pipeline/`](pipeline/README.md): aylık ve senaryo orkestrasyonu
- [`services/`](services/README.md): iç YDA/LCA ve raporlama servisleri
- [`data_schemas/`](data_schemas/README.md): girdi şablonları ve veri sözleşmeleri
- [`outputs/runtime/`](outputs/runtime/README.md): üretilen çalışma zamanı çıktıları

## Hızlı Başlangıç

```bash
pip install -r requirements.txt
python -m app.app
```

Açın: `http://127.0.0.1:5050`

## Minimal Demo Akışı

1. Gerekli Excel/CSV dosyalarını `outputs/runtime/` içine yerleştirin.
2. Flask uygulamasını `python -m app.app` ile başlatın.
3. Tarayıcıda kontrol panelini açın.
4. Aylık veri ve pipeline sayfalarını kullanarak girdileri hazırlayın ve aylık pipeline çalıştırın.
5. `outputs/runtime/` içindeki üretilen dosyaları inceleyin; özellikle:
   - `matches_LCA_{YYYY-MM}.xlsx`
   - `process_capacity_monthly_{YYYY-MM}.xlsx`
   - `selected_matches_{YYYY-MM}.xlsx`

## Aylık Pipeline Çalıştırma

Uygulama, çalışma dizininin depo kökü olmasını bekler. Çalışma zamanı dosyaları `outputs/runtime/` içinden okunur ve yine buraya yazılır.

Gerekli referans dosyaları mevcutsa aylık pipeline hem arayüzden hem de `pipeline` paketi üzerinden programatik olarak tetiklenebilir.

## Senaryo Çalıştırmaları

Senaryo analizi, mevcut bir aylık çalışmayı temel alır ve puanlama ile optimizasyonu yeniden çalıştırmadan önce değiştirilmiş atık veya kapasite koşullarını uygular.

Örnek:

```python
from pipeline.scenario import ScenarioWasteBounds, run_scenario_pipeline

run_scenario_pipeline(
    1,
    "2026-05",
    waste_bounds=ScenarioWasteBounds(global_max_kg_month=1e6),
)
```

## Configuration

| Değişken | Anlamı |
|---|---|
| `LCA_API_URL` / `LCA_SERVICE_URL` | LCA temel adresi; varsayılan olarak yerel Flask uygulamasındaki `/api/lca` kullanılır |
| `GAMS_EXE` | GAMS kullanılacaksa `gams.exe` için mutlak yol |
| `USE_MOCK_LCA` | `1` ise HTTP yerine sahte/mock LCA akışı kullanılır |

Ana yol ayarları `core.config` içinde tanımlanır; buna `RUNTIME_DIR = outputs/runtime` da dahildir.

## İnceleyiciler Önce Neye Bakmalı

- `docs/EVALUATOR_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `app/app.py`
- `pipeline/monthly.py`
- `services/lca/calculator.py`

## Paketleme Notları

Bu depoyu zip olarak paylaşırken:

- `.venv/` klasörünü dahil etmeyin
- `__pycache__/` klasörünü dahil etmeyin
- Demo parçası değilse büyük geçici çıktıları dahil etmeyin
- İnceleyicilerin tekrar üretilebilir bir akış görmesi gerekiyorsa küçük ve temsilî bir çalışma zamanı girdi/çıktı örneği ekleyin
