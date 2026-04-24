# pipeline

Aylık çalıştırmalar, senaryolar ve simülasyon için iş akışı orkestrasyon katmanı.

## Sorumluluklar

- aylık pipeline çalıştırma
- senaryo pipeline çalıştırma
- dijital ikiz tarzı simülasyon yardımcıları
- seçili sonuçları dışa aktarma

## Temel Dosyalar

- `monthly.py`: ana aylık orkestrasyon
- `scenario.py`: senaryo tabanlı yeniden çalıştırmalar ve kısıtlar
- `digital_twin.py`: simülasyon odaklı ayarlamalar
- `selected_export.py`: seçili çıktı dışa aktarım yardımcıları

## Girdiler

Referans ve çalışma zamanı verilerini `outputs/runtime/` içinden, ortak mantığı ise `core/` katmanından okur.

## Çıktılar

Üretilen eşleşme, kapasite ve seçim dosyalarını tekrar `outputs/runtime/` içine yazar.
