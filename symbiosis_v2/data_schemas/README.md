# Veri şemaları ve şablonlar

- **`templates/`** — Excel/CSV şablonları; **yalnızca zorunlu sütun başlıkları** (detay ve isteğe bağlı alanlar için bkz. `column_dictionary.md`).
- **`column_dictionary.md`** — Tablo bazlı kolonlar, tipler, FK ilişkileri, `matches_LCA` / GAMS alanları ve örnek satırlar.
- Yeni: `process_metadata.xlsx`, `bref_emission_limits.xlsx`; `processes` ve `waste_coefficients` şablonlarına ek kolonlar (bkz. sözlük §2, §4, §4b, §4c).

Üretilen çalışma dosyaları (`matches_LCA_YYYY-MM.xlsx` vb.) genelde `../data/runtime/` altında tutulması önerilir (pipeline yapılandırması ile).
