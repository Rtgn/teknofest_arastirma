# file: scripts/generate_resource_use_template.py

#import pandas as pd
#from pathlib import Path
#from config import DATA_SCHEMAS_DIR
#
#def generate_resource_use_template():
#    """
#    process_metadata.xlsx içindeki min/max kolonlarından
#    proses başına ton ürün için ortalama kaynak kullanımı çıkarır
#    ve resource_use_template.csv olarak kaydeder.
#    """
#    meta_path = Path(DATA_SCHEMAS_DIR) / "process_metadata.xlsx"
#    out_path = Path(DATA_SCHEMAS_DIR)  / "resource_use_template.xlsx"
#
#    df = pd.read_excel(meta_path)
#
#    required_cols = [
#        "process_id",
#        "water_min", "water_max",
#        "energy_min", "energy_max",
#        "electricity_min", "electricity_max",
#        "chemicals_min", "chemicals_max",
#        "yield_min", "yield_max",
#    ]
#    missing = [c for c in required_cols if c not in df.columns]
#    if missing:
#        raise ValueError(f"process_metadata.xlsx eksik kolonlar: {missing}")
#
#    # Ortalama değerler (ton ürün başına)
#    # Not: energy_min/max varsa bunu örneğin 'thermal_energy' gibi düşünebilirsin
#    resource_rows = []
#
#    for _, row in df.iterrows():
#        pid = row["process_id"]
#
#        def avg(col_min, col_max):
#            return float(row[col_min] + row[col_max]) / 2.0
#
#        water_use = avg("water_min", "water_max")
#        energy_use = avg("energy_min", "energy_max")
#        electricity_use = avg("electricity_min", "electricity_max")
#        chemicals_use = avg("chemicals_min", "chemicals_max")
#
#        # yield_min/max ileride verim düzeltmesi için kullanılabilir;
#        # şimdilik doğrudan 1 ton ürün varsayıyoruz.
#
#        resource_rows.append({
#            "process_id": pid,
#            "water_m3_per_ton": water_use,
#            "thermal_energy_kwh_per_ton": energy_use,
#            "electricity_kwh_per_ton": electricity_use,
#            "chemicals_kg_per_ton": chemicals_use,
#        })
#
#    out_df = pd.DataFrame(resource_rows)
#    out_df.to_excel(out_path, index=False)
#    print(f"[OK] resource_use_template.xlsx created at: {out_path}")
#
#
#if __name__ == "__main__":
#    generate_resource_use_template()
#

# file: scripts/generate_resource_emission_template.py

import pandas as pd
from pathlib import Path
from config import DATA_SCHEMAS_DIR

def generate_resource_emission_template():
    """
    Kaynak → CO2 emisyon faktörleri için sabit bir tablo üretir.
    Değerler örnek/placeholder; literatüre göre güncellenebilir.
    """
    out_path = Path(DATA_SCHEMAS_DIR) / "resource_emission_template.xlsx"

    data = [
        {
            "resource_type": "electricity",
            "emission_factor": 0.42,  # kg CO2 / kWh (örnek)
            "unit": "kg_CO2_per_kWh",
            "source": "Example grid factor (update with TEİAŞ/IPCC)",
        },
        {
            "resource_type": "thermal_energy",
            "emission_factor": 0.25,  # kg CO2 / kWh (örnek, doğalgaz/buhar karışık)
            "unit": "kg_CO2_per_kWh",
            "source": "Example natural gas/steam mix",
        },
        {
            "resource_type": "water",
            "emission_factor": 0.0003,  # kg CO2 / m3 (örnek)
            "unit": "kg_CO2_per_m3",
            "source": "Example water treatment & pumping",
        },
        {
            "resource_type": "chemicals",
            "emission_factor": 1.5,  # kg CO2 / kg (tamamen örnek)
            "unit": "kg_CO2_per_kg",
            "source": "Generic chemicals footprint (placeholder)",
        },
    ]

    df = pd.DataFrame(data)
    df.to_csv(out_path, index=False)
    print(f"[OK] resource_emission_template.csv created at: {out_path}")


if __name__ == "__main__":
    generate_resource_emission_template()
