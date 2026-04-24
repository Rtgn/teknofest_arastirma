# core

Ortak iş mantığı ve uygulama genelinde kullanılan sözleşmeler.

## Sorumluluklar

- yapılandırma ve ortam değişkenleri
- dönem ayrıştırma ve dosya adlandırma
- kimlik ayrıştırma ve normalizasyon
- puanlama ve türetilmiş metrikler
- LCA istemci entegrasyonu
- veri temizleme ve eşleştirme desteği

## Temel Dosyalar

- `config.py`: yol ve ortam yapılandırması
- `period.py`: dönem ayrıştırma ve dosya adı yardımcıları
- `scoring.py`: sürdürülebilirlik puanlama mantığı
- `lca_client.py`: LCA istek/yanıt entegrasyonu
- `factory_ids.py`: fabrika kimliği normalizasyonu

## Kullanan Modüller

- `app/`
- `pipeline/`
- `services/`
- `optimization/`
