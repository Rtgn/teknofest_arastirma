import os
import pandas as pd
from database import engine, SessionLocal, Base
from models import ProcessLCAProfile, EmissionFactor

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Eğer veri varsa atla
    if db.query(ProcessLCAProfile).first():
        print("LCA DB zaten dolu.")
        db.close()
        return

    # Varsayılan emisyon faktörleri
    factors = [
        EmissionFactor(resource_type="electricity", co2_per_unit=0.42, unit="kWh", description="Grid electricity Turkey"),
        EmissionFactor(resource_type="water", co2_per_unit=0.0003, unit="m3", description="Mains water supply"),
        EmissionFactor(resource_type="chemical", co2_per_unit=2.1, unit="kg", description="Generic chemical mix"),
        EmissionFactor(resource_type="transport_truck", co2_per_unit=0.062, unit="ton-km", description="Heavy duty truck"),
    ]
    db.add_all(factors)

    # Elimizdeki proseslere (process.xlsx'e dayanarak) varsayılan LCA profilleri ekle
    # Gerçek uygulamada bu OSB proseslerinden çekilmeli.
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    proc_file = os.path.join(base_dir, "process.xlsx")
    if os.path.exists(proc_file):
        df = pd.read_excel(proc_file)
        profiles = []
        for pid in df["process_id"].unique():
            # Sektöre (NACE) veya tipe göre rastgele/gerçekçi değişimler yapılabilir
            # Şimdilik standart baz değerler
            profiles.append(ProcessLCAProfile(
                process_id=str(pid),
                energy_kwh_per_ton=50.0,
                water_m3_per_ton=1.5,
                chemical_kg_per_ton=0.2,
                recovery_efficiency=0.85
            ))
        db.add_all(profiles)

    db.commit()
    db.close()
    print("LCA DB başarıyla başlatıldı ve dolduruldu.")

if __name__ == "__main__":
    init_db()
