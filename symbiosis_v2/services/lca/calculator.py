from sqlalchemy.orm import Session
from core.config import RUNTIME_DIR

from .models import ProcessLCAProfile, EmissionFactor
import pandas as pd
import os

# Mevcut eski kaynak emisyonlarını global olarak yükleyelim ki
# tamamen bağımsız çalışabilsin
BASE_DIR = str(RUNTIME_DIR)

def load_legacy_factors():
    try:
        eff = pd.read_excel(os.path.join(BASE_DIR, "resource_emission.xlsx"))
        return dict(zip(eff["resource_type"], eff["emission_factor_kg_co2_per_unit"]))
    except:
        return {}

def load_waste_recovery_legacy():
    try:
        wr = pd.read_excel(os.path.join(BASE_DIR, "waste_recovery.xlsx"))
        return wr.set_index("Waste ID")[["Recovery Rate", "Target Resource Type"]].to_dict("index")
    except:
        return {}

def load_economic_legacy():
    try:
        ru = pd.read_excel(os.path.join(BASE_DIR, "resource_use.xlsx"))
        return dict(zip(ru["resource_type"], ru["cost_per_unit"]))
    except:
        return {}

def load_disposal_cost_legacy():
    try:
        wm = pd.read_excel(os.path.join(BASE_DIR, "waste_streams.xlsx"))
        return dict(zip(wm["waste_id"], wm["disposal_cost_per_ton"]))
    except:
        return {}

# RAM'e al
LEGACY_EMISSIONS = load_legacy_factors()
LEGACY_RECOVERY = load_waste_recovery_legacy()
LEGACY_PRICES = load_economic_legacy()
LEGACY_DISPOSAL = load_disposal_cost_legacy()

def calculate_lca(
    db: Session,
    process_id: str,
    waste_id: str,
    waste_amount_kg: float,
    distance_km: float,
    transport_mode: str = "transport_truck"
):
    """
    Spesifik bir eşleşmenin detaylı LCA ve Ekonomik metriklerini hesaplar.

    Çevre Ağırlıklı Versiyon (v2, IPCC AR6 uyumlu):
    - Önlenen bertaraf CO₂: 120 kg/ton (Landfill CH4 + leachate, EPA/IPCC AR6)
    - Taşıma emisyon faktörü: 0.089 kg CO₂/ton-km (EEA Road Freight 2023)
    - Net CO₂ = (Önlenen bertaraf + Önlenen hammadde) - (Taşıma + İşleme)
    """
    waste_amount_ton = waste_amount_kg / 1000.0 if waste_amount_kg else 0.0

    # 1. Profil ve Faktörleri Çek
    profile = db.query(ProcessLCAProfile).filter_by(process_id=process_id).first()
    if not profile:
        # Fallback profile
        profile = ProcessLCAProfile(
            energy_kwh_per_ton=50.0, water_m3_per_ton=1.5, chemical_kg_per_ton=0.2, recovery_efficiency=0.85
        )

    t_factor = db.query(EmissionFactor).filter_by(resource_type=transport_mode).first()
    transport_co2_kg_per_ton_km = t_factor.co2_per_unit if t_factor else 0.089  # EEA Road Freight 2023

    e_factor = db.query(EmissionFactor).filter_by(resource_type="electricity").first()
    grid_co2 = e_factor.co2_per_unit if e_factor else 0.42

    # 2. Önlenen Bertaraf (Avoided Disposal)
    # IPCC AR6 Landfill emisyon faktörü: depolama alanı metan (CH4) + sızdırma
    # ~100-140 kg CO2e/ton aralığı → merkezi değer 120 kullanılıyor
    avoided_disposal_co2 = waste_amount_ton * 120.0  # kg CO2e/ton (IPCC AR6)
    disposal_cost_saving = waste_amount_ton * LEGACY_DISPOSAL.get(waste_id, 50.0) # Ton başı bertaraf kurtarımı

    # 3. Geri Kazanım ve Önlenen Hammadde (Recovery & Avoided Virgin Material)
    rec_info = LEGACY_RECOVERY.get(waste_id, {"Recovery Rate": 0.8, "Target Resource Type": "Unknown"})
    # Verimi profile the bağla: (Veritabanındaki verim * Exceldeki rate)
    eff = profile.recovery_efficiency
    final_recovery_rate = rec_info["Recovery Rate"] * eff
    recovered_amount_kg = waste_amount_kg * final_recovery_rate

    target_res = rec_info["Target Resource Type"]
    res_co2_factor = LEGACY_EMISSIONS.get(target_res, 0.0) # Virgin material CO2

    avoided_virgin_co2 = recovered_amount_kg * res_co2_factor

    # 4. İşleme Yükü (Processing Burden)
    # Prosesin bu atığı işlerken harcadığı elektrik vb.
    processing_energy_kwh = waste_amount_ton * profile.energy_kwh_per_ton
    processing_co2 = processing_energy_kwh * grid_co2

    # 5. Taşıma Yükü (Transport Burden)
    transport_co2 = waste_amount_ton * distance_km * transport_co2_kg_per_ton_km

    # 6. NET CO2 HESABI (tCO2e)
    # Net = Önlenenler - Harcananlar
    net_co2e_kg = (avoided_disposal_co2 + avoided_virgin_co2) - (processing_co2 + transport_co2)
    net_co2e_ton = net_co2e_kg / 1000.0

    # 7. EKONOMİK HESAP
    # Kâr = (Geri Kazanılan Hammadenin Değeri + Önlenen Çöp Masrafı) - (Taşıma + İşleme Masrafı)
    res_price = LEGACY_PRICES.get(target_res, 0.5)
    recovered_value = recovered_amount_kg * res_price
    
    transport_cost = waste_amount_ton * distance_km * 0.1 # 0.1$/ton-km
    processing_cost = processing_energy_kwh * 0.2         # 0.2$/kWh

    profit = (recovered_value + disposal_cost_saving) - (transport_cost + processing_cost)

    return {
        "waste_amount_monthly": waste_amount_kg,
        "recovered_mass_monthly": recovered_amount_kg,
        "transport_cost": round(transport_cost, 2),
        "avoided_disposal_cost": round(disposal_cost_saving, 2),
        "processing_cost": round(processing_cost, 2),
        "recovered_value": round(recovered_value, 2),
        "profit": round(profit, 2),
        # Bileşenler küçük olduğunda 3 hanede 0 görünmesin diye 6 hane (tCO2e)
        "transport_co2": round(transport_co2 / 1000.0, 6),
        "processing_co2": round(processing_co2 / 1000.0, 6),
        "avoided_co2": round((avoided_disposal_co2 + avoided_virgin_co2) / 1000.0, 6),
        "net_co2e": round(net_co2e_ton, 6),
    }
