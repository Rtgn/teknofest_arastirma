# Proje Yapısı

Bu dosya, inceleyiciler için deponun hızlı bir haritasını sunar.

```text
teknofest_arastirma/
├── app/                 Flask arayüzü ve yerel HTTP uç noktaları
├── core/                Ortak iş kuralları, yapılandırma, ayrıştırma, puanlama
├── data_schemas/        Girdi şablonları ve sütun sözleşmeleri
├── docs/                Mimari ve değerlendiriciye yönelik dokümantasyon
├── optimization/        GAMS/optimizasyon entegrasyonu ve sonuç okuyucuları
├── outputs/
│   └── runtime/         Çalışma zamanı girdileri ve üretilen çıktılar
├── pipeline/            Aylık ve senaryo orkestrasyonu
├── services/
│   ├── lca/             Yerel LCA servis mantığı ve SQLite modelleri
│   └── reporter/        Raporlama yardımcıları ve prompt dosyaları
└── utils/               Tek seferlik yardımcı betikler ve üreticiler
```

## Klasör Sorumlulukları

### `app/`

Flask giriş noktasını, şablonları, statik varlıkları ve arayüz odaklı veri erişim yardımcılarını içerir.

### `core/`

Yapılandırma, puanlama, dönem işleme, kimlik ayrıştırma, LCA istemci sözleşmeleri ve veri hazırlama yardımcıları gibi yeniden kullanılabilir alan mantığını içerir.

### `pipeline/`

Aylık çalıştırmalar, senaryo çalıştırmaları, dijital ikiz simülasyonu ve seçilen çıktıların dışa aktarımı için orkestrasyon mantığını içerir.

### `services/`

İç servisleri içerir:

- `lca/`: yerel yaşam döngüsü değerlendirmesi hesaplamaları ve profil/faktör kalıcılığı
- `reporter/`: rapor üretim mantığı ve prompt şablonları

### `optimization/`

GAMS odaklı CSV hazırlama ve sonuç çıkarımı dahil olmak üzere optimizasyon çevresindeki üretici ve okuyucu bileşenleri içerir.

### `data_schemas/`

Girdilerin açık ve denetlenebilir kalması için Excel/CSV şablonları ile şema seviyesinde dokümantasyonu içerir.

### `outputs/runtime/`

Yerel çalıştırmalar sırasında kullanılan ve üretilen çalışma dosyalarını içerir. Uygulama ile pipeline arasındaki ana çalışma zamanı alışveriş noktası burasıdır.

### `docs/`

Kod tabanının derin kaynak incelemesi olmadan anlaşılabilmesi için inceleyici odaklı açıklamaları içerir.

### `utils/`

Geliştirme veya veri hazırlığı sırasında faydalı olan ancak ana uygulama akışının parçası olmayan küçük yardımcı betikleri içerir.
