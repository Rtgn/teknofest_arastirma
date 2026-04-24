from sqlalchemy import Column, Integer, String, Float
from .database import Base

class ProcessLCAProfile(Base):
    __tablename__ = "process_lca_profiles"

    process_id = Column(String, primary_key=True, index=True)
    energy_kwh_per_ton = Column(Float, default=50.0)
    water_m3_per_ton = Column(Float, default=1.5)
    chemical_kg_per_ton = Column(Float, default=0.2)
    waste_reduction_coeff = Column(Float, default=1.0)
    recovery_efficiency = Column(Float, default=0.85)

class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    resource_type = Column(String, primary_key=True, index=True)
    co2_per_unit = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    description = Column(String)
