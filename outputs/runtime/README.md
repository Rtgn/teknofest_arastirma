# outputs/runtime

Yerel çalıştırmalar için çalışma zamanı alışveriş dizini.

## Amaç

Bu klasör, uygulamanın çalışma girdi dosyalarını okuduğu ve üretilen çıktı dosyalarını yazdığı ana dizindir.

## Tipik Girdiler

- `factories.xlsx`
- `processes.xlsx`
- `waste_streams.xlsx`
- `waste_process_links.xlsx`
- `process_capacity.csv`
- aylık durum ve kapasite faktörü dosyaları

## Tipik Çıktılar

- `matches_LCA_{YYYY-MM}.xlsx`
- `process_capacity_monthly_{YYYY-MM}.xlsx`
- `selected_matches_{YYYY-MM}.xlsx`

## Notlar

- bu klasör, bu README dışında bilinçli olarak git tarafından yok sayılır
- değerlendiriciler, sistemin somut girdi ve çıktılarını anlamak için bir çalıştırmadan sonra bu klasörü inceleyebilir
