# optimization

Symbiosis MILP çözücü katmanı.

## Sorumluluklar

- eşleşme tablosundan MILP kurup çözmek (atık/proses/OSB kısıtları altında sürdürülebilirlik + çevresel skoru maksimize eder)
- seçili eşleşme sonuçlarını tekrar uygulamaya okumak

## Temel Dosyalar

- `pulp_symbiosis.py`: PuLP + CBC ile symbiosis MILP çözücü; `selected_matches.csv` (`match_id;level`) yazar
- `result_reader.py`: `selected_matches.csv` + ilgili `matches_LCA_*.xlsx` dosyasından seçilen satırları döndürür

## Notlar

- bu katman, optimizasyon sorumlulukları izole kalsın diye `core/` katmanından bilinçli olarak ayrılmıştır
- yalnızca `pulp` (CBC varsayılan) gereklidir; ek kurulum yok
