import os

import pandas as pd
from sqlalchemy.orm import Session

from core.config import RUNTIME_DIR

from .models import EmissionFactor, ProcessLCAProfile

# Mevcut eski kaynak emisyonlarını global olarak yükleyelim ki
# tamamen bağımsız çalışabilsin
BASE_DIR = str(RUNTIME_DIR)
DEFAULT_RECOVERY = {"Recovery Rate": 0.8, "Target Resource Type": "Unknown"}
FALLBACK_PROFILE = {
    "energy_kwh_per_ton": 50.0,
    "water_m3_per_ton": 1.5,
    "chemical_kg_per_ton": 0.2,
    "recovery_efficiency": 0.85,
}
TRANSPORT_COST_PER_TON_KM = 0.1
PROCESSING_COST_PER_KWH = 0.2
AVOIDED_DISPOSAL_CO2_PER_TON = 120.0


def _read_legacy_excel(filename: str, builder):
    try:
        return builder(pd.read_excel(os.path.join(BASE_DIR, filename)))
    except Exception:
        return {}


# RAM'e al
LEGACY_EMISSIONS = _read_legacy_excel(
    "resource_emission.xlsx",
    lambda df: dict(zip(df["resource_type"], df["emission_factor_kg_co2_per_unit"])),
)
LEGACY_RECOVERY = _read_legacy_excel(
    "waste_recovery.xlsx",
    lambda df: df.set_index("Waste ID")[["Recovery Rate", "Target Resource Type"]].to_dict("index"),
)
LEGACY_PRICES = _read_legacy_excel(
    "resource_use.xlsx",
    lambda df: dict(zip(df["resource_type"], df["cost_per_unit"])),
)
LEGACY_DISPOSAL = _read_legacy_excel(
    "waste_streams.xlsx",
    lambda df: dict(zip(df["waste_id"], df["disposal_cost_per_ton"])),
)
DEFAULT_DISPOSAL_COST_PER_TON = 50.0
DEFAULT_RESOURCE_PRICE = 0.5
DEFAULT_TRANSPORT_CO2 = 0.089
DEFAULT_GRID_CO2 = 0.42


def _fallback_profile() -> ProcessLCAProfile:
    return ProcessLCAProfile(**FALLBACK_PROFILE)


def _emission_factor(db: Session, resource_type: str, default: float) -> float:
    factor = db.query(EmissionFactor).filter_by(resource_type=resource_type).first()
    return factor.co2_per_unit if factor else default


def _profile(db: Session, process_id: str) -> ProcessLCAProfile:
    return db.query(ProcessLCAProfile).filter_by(process_id=process_id).first() or _fallback_profile()


def _round_tons(value_kg: float) -> float:
    return round(value_kg / 1000.0, 6)


def calculate_lca(
    db: Session,
    process_id: str,
    waste_id: str,
    waste_amount_kg: float,
    distance_km: float,
    transport_mode: str = "transport_truck",
):
    """
    Belirli bir eşleşme için ayrıntılı LCA ve ekonomik metrikleri hesaplar.

    Çevre ağırlıklı sürüm (v2, IPCC AR6 uyumlu):
    - Önlenen bertaraf CO₂: 120 kg/ton (depolama alanı CH4 + sızıntı, EPA/IPCC AR6)
    - Taşıma emisyon faktörü: 0.089 kg CO₂/ton-km (EEA Road Freight 2023)
    - Net CO₂ = (önlenen bertaraf + önlenen hammadde) - (taşıma + işleme)
    """
    waste_amount_ton = waste_amount_kg / 1000.0 if waste_amount_kg else 0.0
    profile = _profile(db, process_id)
    transport_co2_kg_per_ton_km = _emission_factor(db, transport_mode, DEFAULT_TRANSPORT_CO2)
    grid_co2 = _emission_factor(db, "electricity", DEFAULT_GRID_CO2)

    # 2. Önlenen bertaraf
    # IPCC AR6 Landfill emisyon faktörü: depolama alanı metan (CH4) + sızdırma
    # ~100-140 kg CO2e/ton aralığı → merkezi değer 120 kullanılıyor
    avoided_disposal_co2 = waste_amount_ton * AVOIDED_DISPOSAL_CO2_PER_TON
    disposal_cost_saving = waste_amount_ton * LEGACY_DISPOSAL.get(waste_id, DEFAULT_DISPOSAL_COST_PER_TON)

    # 3. Geri kazanım ve önlenen hammadde
    rec_info = LEGACY_RECOVERY.get(waste_id, DEFAULT_RECOVERY)
    final_recovery_rate = rec_info["Recovery Rate"] * profile.recovery_efficiency
    recovered_amount_kg = waste_amount_kg * final_recovery_rate

    target_res = rec_info["Target Resource Type"]
    avoided_virgin_co2 = recovered_amount_kg * LEGACY_EMISSIONS.get(target_res, 0.0)

    # 4. İşleme yükü
    # Prosesin bu atığı işlerken harcadığı elektrik vb.
    processing_energy_kwh = waste_amount_ton * profile.energy_kwh_per_ton
    processing_co2 = processing_energy_kwh * grid_co2

    # 5. Taşıma yükü
    transport_co2 = waste_amount_ton * distance_km * transport_co2_kg_per_ton_km

    # 6. NET CO2 HESABI (tCO2e)
    # Net = Önlenenler - Harcananlar
    avoided_co2 = avoided_disposal_co2 + avoided_virgin_co2
    net_co2e_kg = avoided_co2 - (processing_co2 + transport_co2)

    # 7. EKONOMİK HESAP
    # Kâr = (Geri Kazanılan Hammadenin Değeri + Önlenen Çöp Masrafı) - (Taşıma + İşleme Masrafı)
    recovered_value = recovered_amount_kg * LEGACY_PRICES.get(target_res, DEFAULT_RESOURCE_PRICE)
    transport_cost = waste_amount_ton * distance_km * TRANSPORT_COST_PER_TON_KM
    processing_cost = processing_energy_kwh * PROCESSING_COST_PER_KWH
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
        "transport_co2": _round_tons(transport_co2),
        "processing_co2": _round_tons(processing_co2),
        "avoided_co2": _round_tons(avoided_co2),
        "net_co2e": _round_tons(net_co2e_kg),
    }
