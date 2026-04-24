# app

Projenin Flask uygulama katmanı.

## Sorumluluklar

- kontrol paneli ve arayüz sayfaları
- aylık girdi yönetimi uç noktaları
- simülasyon uç noktaları
- pipeline tetikleme uç noktaları
- yerel LCA HTTP rotaları

## Temel Dosyalar

- `app.py`: Flask giriş noktası ve rota tanımları
- `data_access.py`: çalışma zamanı çıktılarından arayüz odaklı okumalar
- `monthly_data_io.py`: aylık girdi okuma/yazma yardımcıları
- `templates/`: sayfa şablonları
- `static/`: CSS ve statik varlıklar

## Bağımlı Olduğu Klasörler

- `core/`
- `pipeline/`
- `services/lca/`
- `outputs/runtime/`
