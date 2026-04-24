# optimization

Optimizasyon entegrasyon katmanı.

## Sorumluluklar

- optimizasyon girdi tablolarını hazırlamak
- dış optimizasyon iş akışını çağırmak
- seçili eşleşme sonuçlarını tekrar uygulamaya okumak

## Temel Dosyalar

- `gdx_builder.py`: optimizasyon odaklı CSV girdilerini hazırlar
- `gams_runner.py`: GAMS'ı alt süreç çağrısı ile çalıştırır
- `result_reader.py`: seçili eşleşme çıktılarını okur
- `gms/`: GAMS tarafındaki model dosyaları ve notlar

## Notlar

- bu katman, optimizasyon sorumlulukları izole kalsın diye `core/` katmanından bilinçli olarak ayrılmıştır
- tam optimizasyon yolu için GAMS'ın ortamda bulunması gerekir
