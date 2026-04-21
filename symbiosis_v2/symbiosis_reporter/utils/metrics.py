import pandas as pd

def compute_monthly_change(current_metrics, previous_metrics):
    changes = {}
    for key, curr_val in current_metrics.items():
        if isinstance(curr_val, (int, float)):
            prev_val = previous_metrics.get(key, 0.0)
            if prev_val == 0:
                if curr_val > 0:
                    changes[f"change_{key}"] = 100.0
                elif curr_val < 0:
                    changes[f"change_{key}"] = -100.0
                else:
                    changes[f"change_{key}"] = 0.0
            else:
                change = ((curr_val - prev_val) / abs(prev_val)) * 100
                changes[f"change_{key}"] = round(change, 2)
    return changes

def factory_metrics(df, factory_id, previous_df=None):
    def _calc_metrics(data_df):
        df_source = data_df[data_df['source_factory'] == factory_id]
        total_sent = df_source['waste_amount_monthly'].sum() if 'waste_amount_monthly' in data_df.columns else 0.0
        
        df_target = data_df[data_df['target_factory'] == factory_id]
        total_received = df_target['recovered_mass_monthly'].sum() if 'recovered_mass_monthly' in data_df.columns else 0.0

        df_factory = data_df[(data_df['source_factory'] == factory_id) | (data_df['target_factory'] == factory_id)]
        
        total_profit = df_factory['profit'].sum() if 'profit' in data_df.columns else 0.0
        total_transport_cost = df_factory['transport_cost'].sum() if 'transport_cost' in data_df.columns else 0.0
        total_avoided = df_factory['avoided_emissions'].sum() if 'avoided_emissions' in data_df.columns else 0.0
        total_net = df_factory['net_co2e'].sum() if 'net_co2e' in data_df.columns else 0.0
        
        electricity = df_factory['electricity_kwh'].sum() if 'electricity_kwh' in data_df.columns else 0.0
        thermal = df_factory['thermal_energy_kwh'].sum() if 'thermal_energy_kwh' in data_df.columns else 0.0
        water = df_factory['water_m3'].sum() if 'water_m3' in data_df.columns else 0.0

        best_partner = "Yok"
        best_waste = "Yok"
        best_score = 0.0
        
        if not df_factory.empty and 'sustainability_score' in data_df.columns:
            # En son çıkan en iyi skoru bulalım
            best_match = df_factory.loc[df_factory['sustainability_score'].idxmax()]
            if best_match['source_factory'] == factory_id:
                best_partner = best_match['target_factory']
            else:
                best_partner = best_match['source_factory']
            best_waste = best_match['waste_id'] if 'waste_id' in data_df.columns else "Bilinmiyor"
            best_score = best_match['sustainability_score']

        return {
            "total_sent": round(total_sent, 2),
            "total_received": round(total_received, 2),
            "total_profit": round(total_profit, 2),
            "total_transport_cost": round(total_transport_cost, 2),
            "total_avoided": round(total_avoided, 4),
            "total_net": round(total_net, 4),
            "electricity": round(electricity, 2),
            "thermal": round(thermal, 2),
            "water": round(water, 2),
            "best_partner": best_partner,
            "best_waste": best_waste,
            "best_score": round(best_score, 4)
        }

    current = _calc_metrics(df)
    result = {"factory_id": factory_id, **current}

    if previous_df is not None:
        previous = _calc_metrics(previous_df)
        changes = compute_monthly_change(current, previous)
        result.update(changes)
        result["has_previous"] = True
    else:
        result["has_previous"] = False

    return result

def osb_metrics(df, previous_df=None):
    def _calc_metrics(data_df):
        match_count = len(data_df)
        total_recovered = data_df['recovered_mass_monthly'].sum() if 'recovered_mass_monthly' in data_df.columns else 0.0
        total_avoided = data_df['avoided_emissions'].sum() if 'avoided_emissions' in data_df.columns else 0.0
        total_net = data_df['net_co2e'].sum() if 'net_co2e' in data_df.columns else 0.0
        total_transport_emissions = data_df['transport_emissions'].sum() if 'transport_emissions' in data_df.columns else 0.0
        avg_distance = data_df['distance_km'].mean() if 'distance_km' in data_df.columns else 0.0
        
        top_sources = ""
        top_targets = ""
        
        if not data_df.empty:
            if 'source_factory' in data_df.columns:
                top_sources_counts = data_df['source_factory'].value_counts()
                top_sources = ", ".join(top_sources_counts.head(3).index.tolist())
            if 'target_factory' in data_df.columns:
                top_targets_counts = data_df['target_factory'].value_counts()
                top_targets = ", ".join(top_targets_counts.head(3).index.tolist())

        return {
            "match_count": match_count,
            "total_recovered": round(total_recovered, 2),
            "total_avoided": round(total_avoided, 4),
            "total_net": round(total_net, 4),
            "total_transport_emissions": round(total_transport_emissions, 6),
            "avg_distance": round(avg_distance, 2) if not pd.isna(avg_distance) else 0.0,
            "top_sources": top_sources,
            "top_targets": top_targets
        }

    current = _calc_metrics(df)
    result = {**current}

    if previous_df is not None:
        previous = _calc_metrics(previous_df)
        changes = compute_monthly_change(current, previous)
        result.update(changes)
        result["has_previous"] = True
    else:
        result["has_previous"] = False

    return result
