# Sayısal Sabitler

| Sabit Adı | Açıklama | Sabit Değeri | Birim |
| --- | --- | ---: | --- |
| `_SYNTH_CENTER_LAT` | Sahte fabrika harita konumları üretilmesi gerektiğinde kullanılan merkez enlem değeri. | 39.0 | derece enlem |
| `_SYNTH_CENTER_LNG` | Sahte fabrika harita konumları üretilmesi gerektiğinde kullanılan merkez boylam değeri. | 35.0 | derece boylam |
| `_SYNTH_RADIUS_DEG` | Eksik fabrika koordinatları için kullanılan sentetik yerleştirme çemberinin yarıçapı. | 0.45 | derece |
| `DEFAULT_TON_PER_DAY` | Kapasite girdisi eksik olduğunda kullanılan varsayılan günlük proses kapasitesi. | 10.0 | ton/gün |
| `LITERATURE_TRANSPORT_COST_EUR_PER_TON_KM` | Türetilmiş taşıma maliyetinde kullanılan literatür tabanlı karayolu taşıma katsayısı. | 0.07 | EUR/(ton-km) |
| `TECH_SCORE_DISTANCE_REFERENCE_KM` | Mesafe arttıkça teknik puanı azaltmak için kullanılan referans uzaklık ölçeği. | 50.0 | km |
| `W_PROCESS` | Teknik puan içinde proses bilgisinin ağırlığı. | 0.40 | birimsiz |
| `W_RECOVERY` | Teknik puan içinde geri kazanım oranı bilgisinin ağırlığı. | 0.35 | birimsiz |
| `W_DISTANCE` | Teknik puan içinde mesafe yakınlığının ağırlığı. | 0.25 | birimsiz |
| `EARTH_RADIUS_KM` | Haversine mesafe hesabında kullanılan Dünya yarıçapı. | 6371.0 | km |
| `BIG_CAP_THRESHOLD` | Bu değerin üzerindeki kapasite değerleri PuLP kısıtlarında fiilen sınırsız kabul edilir. | 1e11 | kg/ay |
| `W_ENV_DEFAULT` | PuLP optimizasyon modelindeki varsayılan çevresel amaç ağırlığı. | 0.6 | birimsiz |
| `W_SCORE_DEFAULT` | PuLP optimizasyon modelindeki varsayılan sürdürülebilirlik puanı ağırlığı. | 0.4 | birimsiz |
| `_FACTORY_INACTIVE_EPS` | Bu değere eşit veya daha düşük fabrika aktivite değerleri inaktif kabul edilir. | 1e-9 | birimsiz |
| `_MIN_WASTE_KG_FOR_MILP` | Bu atık miktarının altındaki eşleşmeler MILP çözümünden önce çıkarılır. | 1e-6 | kg/ay |
| `TRANSPORT_COST_PER_TON_KM` | Yerel LCA ekonomik hesabında kullanılan varsayılan taşıma maliyeti. | 0.1 | maliyet/(ton-km) |
| `PROCESSING_COST_PER_KWH` | Yerel LCA ekonomik hesabında kullanılan varsayılan işleme enerjisi maliyeti. | 0.2 | maliyet/kWh |
| `AVOIDED_DISPOSAL_CO2_PER_TON` | Yönlendirilmiş her ton atık için yazılan önlenmiş bertaraf emisyon kredisi. | 120.0 | kg CO2e/ton |
| `DEFAULT_DISPOSAL_COST_PER_TON` | Bertaraf maliyeti bulunamadığında kullanılan varsayılan bertaraf tasarrufu. | 50.0 | maliyet/ton |
| `DEFAULT_RESOURCE_PRICE` | Kaynak fiyatı bulunamadığında kullanılan varsayılan geri kazanılmış kaynak fiyatı. | 0.5 | maliyet/birim |
| `DEFAULT_TRANSPORT_CO2` | Veritabanında taşıma faktörü yoksa kullanılan varsayılan taşıma emisyon faktörü. | 0.089 | kg CO2e/(ton-km) |
| `DEFAULT_GRID_CO2` | Veritabanında şebeke faktörü yoksa kullanılan varsayılan elektrik emisyon faktörü. | 0.42 | kg CO2e/kWh |
