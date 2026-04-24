# Numerical Constants

| Constant Name | Explanation | Constant Value | Unit |
| --- | --- | ---: | --- |
| `_SYNTH_CENTER_LAT` | Default center latitude used when fake factory map positions must be generated. | 39.0 | degrees latitude |
| `_SYNTH_CENTER_LNG` | Default center longitude used when fake factory map positions must be generated. | 35.0 | degrees longitude |
| `_SYNTH_RADIUS_DEG` | Radius of the synthetic placement circle for missing factory coordinates. | 0.45 | degrees |
| `DEFAULT_TON_PER_DAY` | Default daily process capacity used when capacity input is missing. | 10.0 | ton/day |
| `LITERATURE_TRANSPORT_COST_EUR_PER_TON_KM` | Literature-based road transport cost coefficient used in derived transport cost. | 0.07 | EUR/(ton-km) |
| `TECH_SCORE_DISTANCE_REFERENCE_KM` | Distance scale used to reduce technical score as distance increases. | 50.0 | km |
| `W_PROCESS` | Weight of process-level technical information in the tech score. | 0.40 | unitless |
| `W_RECOVERY` | Weight of recovery-rate information in the tech score. | 0.35 | unitless |
| `W_DISTANCE` | Weight of distance proximity in the tech score. | 0.25 | unitless |
| `EARTH_RADIUS_KM` | Earth radius used in the haversine distance calculation. | 6371.0 | km |
| `BIG_CAP_THRESHOLD` | Capacity values above this are treated as effectively unlimited in PuLP constraints. | 1e11 | kg/month |
| `W_ENV_DEFAULT` | Default environmental objective weight in the PuLP optimization model. | 0.6 | unitless |
| `W_SCORE_DEFAULT` | Default sustainability-score objective weight in the PuLP optimization model. | 0.4 | unitless |
| `_FACTORY_INACTIVE_EPS` | Factory activity values at or below this are treated as inactive. | 1e-9 | unitless |
| `_MIN_WASTE_KG_FOR_MILP` | Matches below this waste amount are removed before MILP solving. | 1e-6 | kg/month |
| `TRANSPORT_COST_PER_TON_KM` | Default transport cost used in the local LCA economic calculation. | 0.1 | cost/(ton-km) |
| `PROCESSING_COST_PER_KWH` | Default processing energy cost used in the local LCA economic calculation. | 0.2 | cost/kWh |
| `AVOIDED_DISPOSAL_CO2_PER_TON` | Avoided disposal emissions credit assigned per ton of diverted waste. | 120.0 | kg CO2e/ton |
| `DEFAULT_DISPOSAL_COST_PER_TON` | Default disposal savings used when no disposal-cost lookup exists. | 50.0 | cost/ton |
| `DEFAULT_RESOURCE_PRICE` | Default recovered resource price used when no resource-price lookup exists. | 0.5 | cost/unit |
| `DEFAULT_TRANSPORT_CO2` | Default transport emission factor used when no transport factor exists in the DB. | 0.089 | kg CO2e/(ton-km) |
| `DEFAULT_GRID_CO2` | Default electricity emission factor used when no grid factor exists in the DB. | 0.42 | kg CO2e/kWh |
