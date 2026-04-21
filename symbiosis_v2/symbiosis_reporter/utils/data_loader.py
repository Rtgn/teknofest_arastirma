import pandas as pd

def load_matches(path):
    """Excel dosyasını okuyup DataFrame döndürür ve kolon isimlerini normalize eder."""
    try:
        df = pd.read_excel(path)
        # Sütun isimlerini normalize edelim (boşlukları sil, küçük harf yap)
        df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]
        return df
    except Exception as e:
        print(f"Excel okunurken hata oluştu: {e}")
        return None
