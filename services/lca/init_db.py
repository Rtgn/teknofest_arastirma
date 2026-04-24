import pandas as pd
from core.config import RUNTIME_DIR

from .database import engine, SessionLocal, Base
from .models import ProcessLCAProfile, EmissionFactor

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        added = 0

        # Varsayılan emisyon faktörlerini yalnızca eksikse ekle.
        factor_defs = [
            ("electricity", 0.42, "kWh", "Grid electricity Turkey"),
            ("water", 0.0003, "m3", "Mains water supply"),
            ("chemical", 2.1, "kg", "Generic chemical mix"),
            ("transport_truck", 0.062, "ton-km", "Heavy duty truck"),
        ]
        existing_factors = {
            row[0]
            for row in db.query(EmissionFactor.resource_type).all()
        }
        for resource_type, co2_per_unit, unit, description in factor_defs:
            if resource_type in existing_factors:
                continue
            db.add(
                EmissionFactor(
                    resource_type=resource_type,
                    co2_per_unit=co2_per_unit,
                    unit=unit,
                    description=description,
                )
            )
            added += 1

        # Çalışma zamanı proseslerinden eksik LCA profillerini ekle.
        proc_file = RUNTIME_DIR / "processes.csv"
        if proc_file.exists():
            if proc_file.suffix.lower() in {".xlsx", ".xls"}:
                df = pd.read_excel(proc_file)
            else:
                df = pd.read_csv(proc_file)
            existing_profiles = {
                row[0]
                for row in db.query(ProcessLCAProfile.process_id).all()
            }
            for pid in df["process_id"].dropna().astype(str).str.strip().unique():
                if not pid or pid in existing_profiles:
                    continue
                db.add(
                    ProcessLCAProfile(
                        process_id=pid,
                        energy_kwh_per_ton=50.0,
                        water_m3_per_ton=1.5,
                        chemical_kg_per_ton=0.2,
                        recovery_efficiency=0.85,
                    )
                )
                added += 1

        db.commit()
        if added:
            print(f"LCA DB guncellendi. Yeni kayit sayisi: {added}")
        else:
            print("LCA DB zaten hazir.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
