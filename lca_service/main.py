from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import ProcessLCAProfile, EmissionFactor
from calculator import calculate_lca
from init_db import init_db

# Veritabanını otomatik başlat
init_db()

app = FastAPI(
    title="LCA Modüler Servisi",
    description="OSB Endüstriyel Simbiyoz için mikroservis mimarisinde LCA hesaplama motoru.",
    version="1.0"
)

# --- REQUEST & RESPONSE SCHEMAS ---

class LCAProfileSchema(BaseModel):
    process_id: str
    energy_kwh_per_ton: float
    water_m3_per_ton: float
    chemical_kg_per_ton: float
    recovery_efficiency: float

class CalculateRequestData(BaseModel):
    match_id: str
    process_id: str
    waste_id: str
    waste_amount_kg: float
    distance_km: float
    transport_mode: Optional[str] = "transport_truck"

class CalculateBatchRequest(BaseModel):
    matches: List[CalculateRequestData]

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "LCA Servisi Aktif. Swagger dokümantasyonu için /docs adresine gidin."}

@app.get("/profiles", response_model=List[LCAProfileSchema])
def get_all_profiles(db: Session = Depends(get_db)):
    profiles = db.query(ProcessLCAProfile).all()
    return profiles

@app.get("/profiles/{process_id}", response_model=LCAProfileSchema)
def get_profile(process_id: str, db: Session = Depends(get_db)):
    profile = db.query(ProcessLCAProfile).filter_by(process_id=process_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Proses LCA Profili bulunamadı.")
    return profile

@app.put("/profiles/{process_id}")
def update_profile(process_id: str, data: LCAProfileSchema, db: Session = Depends(get_db)):
    profile = db.query(ProcessLCAProfile).filter_by(process_id=process_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Bulunamadı.")
    
    profile.energy_kwh_per_ton = data.energy_kwh_per_ton
    profile.water_m3_per_ton = data.water_m3_per_ton
    profile.chemical_kg_per_ton = data.chemical_kg_per_ton
    profile.recovery_efficiency = data.recovery_efficiency
    db.commit()
    return {"message": "Profil güncellendi.", "process_id": process_id}

@app.post("/calculate_lca/batch")
def calculate_batch(request: CalculateBatchRequest, db: Session = Depends(get_db)):
    """
    Birden fazla eşleşmeyi topluca (batch) hesaplar ve listesini döner.
    Optimizasyon motorunun asıl kullanacağı uç nokta budur.
    """
    results = {}
    for match in request.matches:
        res = calculate_lca(
            db=db,
            process_id=match.process_id,
            waste_id=match.waste_id,
            waste_amount_kg=match.waste_amount_kg,
            distance_km=match.distance_km,
            transport_mode=match.transport_mode
        )
        results[match.match_id] = res

    return {"status": "success", "results": results}

# uvicorn main:app --port 8001
