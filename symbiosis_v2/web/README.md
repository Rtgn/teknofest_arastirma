# Symbiosis v2 Web Arayüzü

`tk_arastirma/webapp` ile aynı **koyu indigo** tema (`theme.css`: slate arka plan, yeşil/mavi vurgular). Veri doğrudan **`symbiosis_v2/data_runtime/`** altındaki Excel dosyalarından okunur (ORM yok).

## Çalıştırma

Proje kökü `symbiosis_v2` olmalı:

```bash
cd symbiosis_v2
pip install -r web/requirements.txt
python web/app.py
```

Tarayıcı: **http://127.0.0.1:5050**

## Sayfalar

| Rota | İçerik |
|------|--------|
| `/` | Özet KPI + son dönem eşleşme önizlemesi |
| `/network` | Plotly harita (kaynak→hedef fabrika), kaynak seçimi: tüm LCA eşleşmeleri / seçilenler |
| `/pipeline` | `data_runtime` dosya durumu |

## API

- `GET /api/periods` — `matches_LCA_*.xlsx` türevi dönem listesi  
- `GET /api/network/<YYYY-MM>?source=matches_lca|selected` — Plotly uyumlu `nodes` + `edges`  
- `GET /api/network_graph/<YYYY-MM>?source=...` — PyVis HTML (isteğe bağlı; `pyvis` + `networkx`)

## Gereken dosyalar

- `factories.xlsx` — `id` (veya `factory_id`), `lat`, `lng`, `name`  
- `matches_LCA_<dönem>.xlsx` veya `selected_matches_<dönem>.xlsx` — `source_factory`, `target_factory`, tercihen `waste_amount_monthly`, `sustainability_score`, `profit`, `total_CO2` / `net_co2e`

Harita düğümleri yalnızca fabrika koordinatları mevcut ise çizilir.
