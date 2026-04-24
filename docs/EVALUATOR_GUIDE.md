# Değerlendirici Rehberi

Bu rehber, tüm kod tabanını okumadan projeyi hızlıca anlamak isteyen yarışma değerlendiricileri içindir.

## Projenin Amacı

Proje, OSB ölçeğinde endüstriyel simbiyoz analizini destekler. Bir fabrikanın hangi atık akışlarının başka bir proses tarafından kullanılabileceğini belirlemeye yardımcı olur, çevresel ve ekonomik etkiyi tahmin eder ve optimizasyon yoluyla en uygun eşleşme kümesini seçer.

## Temel Değer

Sistem, dört katmanı tek bir iş akışında birleştirir:

1. Yapılandırılmış endüstriyel girdi verisi
2. YDA/LCA tabanlı etki tahmini
3. Bileşik puanlama
4. Optimizasyon tabanlı seçim

Bu yapı, çıktıları yalnızca kural tabanlı bir eşleşme listesinden daha açıklanabilir hale getirir.

## Zip İçinde Neler Var

Depo, açık sorumluluklara sahip modüllere ayrılmıştır:

- `app/`: user interface and local API layer
- `core/`: business rules and reusable logic
- `pipeline/`: monthly and scenario workflows
- `services/lca/`: local LCA logic and lightweight SQLite-backed profiles/factors
- `services/reporter/`: report-generation utilities
- `data_schemas/templates/`: input templates
- `outputs/runtime/`: generated working files

Tam harita için [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) dosyasına bakın.

## Önerilen İnceleme Sırası

Kısıtlı zamanınız varsa şu sırayla inceleyin:

1. [`../README.md`](../README.md)
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`../app/README.md`](../app/README.md)
4. [`../pipeline/README.md`](../pipeline/README.md)
5. [`../services/README.md`](../services/README.md)

## Uçtan Uca Akış

1. Referans dosyaları `outputs/runtime/` içine yerleştirilir.
2. Aylık pipeline eşleşme adaylarını üretir.
3. LCA servisi her aday için etki metriklerini hesaplar.
4. Puanlama, çevresel ve ekonomik boyutları birleştirir.
5. Optimizasyon, uygulanabilir eşleşme alt kümesini seçer.
6. Sonuçlar `outputs/runtime/` içine yazılır ve Flask arayüzünde incelenebilir.

## Ana Girdiler

Tipik gerekli girdiler şunlardır:

- `factories.csv`
- `processes.csv`
- `waste_streams.csv`
- `waste_process_links.csv`
- `process_capacity.csv`
- supporting templates such as resource use, emission factors, and monthly status files

Girdi şeması tanımları [`../data_schemas/README.md`](../data_schemas/README.md) içinde belgelenmiştir.

## Ana Çıktılar

Önemli üretilen çıktılar şunlardır:

- `matches_LCA_{YYYY-MM}.csv`
- `process_capacity_monthly_{YYYY-MM}.csv`
- `selected_matches_{YYYY-MM}.csv`
- optimization support artifacts written during runs

## Temel Demo Nasıl Çalıştırılır

```bash
pip install -r requirements.txt
python -m app.app
```

`http://127.0.0.1:5050` adresini açın.

## Açıklanabilirlik Notları

Proje şu nedenlerle açıklanabilirdir:

- veri sözleşmeleri Excel/CSV şablonlarında açıkça görülebilir
- LCA hesaplama mantığı okunabilir Python kodu ile uygulanmıştır
- mimari, sorumlulukları klasör bazında ayırır
- çalışma zamanı girdi ve çıktıları ayrı bir dizinde tutulur
- optimizasyon, tüm pipeline’ı gizleyen bir kara kutu değil; son seçim katmanıdır

## Bilinen Sınırlar

- Bazı akışlar, `outputs/runtime/` içinde hazırlanmış çalışma zamanı dosyaları bekler.
- Hafif SQLite katmanı LCA profilleri ve faktörleri için kullanılır; ana uygulama verisi ise hâlâ Excel/CSV çalışma zamanı dosyalarını kullanır.
