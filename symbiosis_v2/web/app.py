"""
Symbiosis v2 web: OSB analiz arayüzü (data_runtime dosyalarından beslenir).
Çalıştırma: symbiosis_v2 kökünden: python -m web.app
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_WEB_ROOT = Path(__file__).resolve().parent
_V2_ROOT = _WEB_ROOT.parent
if str(_V2_ROOT) not in sys.path:
    sys.path.insert(0, str(_V2_ROOT))

import pandas as pd
from flask import Flask, jsonify, render_template, request

from core.factory_ids import parse_factory_id
from web.data_access import (
    build_network_payload,
    list_periods_from_runtime,
    load_dashboard_summary,
    load_matches_for_network,
    load_simulation_baseline,
    runtime_dir,
)
from web.monthly_data_io import (
    ensure_monthly_grids,
    explain_capacity_monthly_kg,
    load_monthly_inputs,
    save_capacity_factors,
    save_factory_status,
    save_process_capacity_csv,
    save_process_status,
)

app = Flask(
    __name__,
    template_folder=str(_WEB_ROOT / "templates"),
    static_folder=str(_WEB_ROOT / "static"),
    static_url_path="/static",
)


@app.route("/")
def index():
    periods = list_periods_from_runtime()
    latest = periods[-1] if periods else None
    dashboard_summary = load_dashboard_summary()
    preview_rows = dashboard_summary.get("preview_rows") or []
    preview_period = dashboard_summary.get("latest_period") or latest
    preview_error = dashboard_summary.get("latest_error")
    return render_template(
        "dashboard.html",
        periods=periods,
        latest_period=latest,
        dashboard_summary=dashboard_summary,
        preview_rows=preview_rows,
        preview_error=preview_error,
        preview_period=preview_period,
        runtime_path=str(runtime_dir()),
    )


@app.route("/network")
def network_page():
    periods = list_periods_from_runtime()
    return render_template("network.html", periods=periods)


@app.route("/simulation")
def simulation_page():
    all_p = list_periods_from_runtime()
    base_periods = [p for p in all_p if re.match(r"^\d{4}-\d{2}$", str(p))]
    return render_template("simulation.html", base_periods=base_periods)


@app.route("/monthly-data")
def monthly_data_page():
    all_p = list_periods_from_runtime()
    base_periods = [p for p in all_p if re.match(r"^\d{4}-\d{2}$", str(p))]
    return render_template("monthly_data.html", base_periods=base_periods, runtime_path=str(runtime_dir()))


@app.route("/api/monthly-inputs", methods=["GET"])
def api_monthly_inputs_get():
    return jsonify(load_monthly_inputs(runtime_dir()))


@app.route("/api/monthly-inputs", methods=["POST"])
def api_monthly_inputs_save():
    data = request.get_json(force=True, silent=True) or {}
    rt = runtime_dir()
    try:
        if data.get("factory_status"):
            save_factory_status(rt, data["factory_status"])
        if data.get("process_status"):
            save_process_status(rt, data["process_status"])
        if data.get("capacity_factors"):
            save_capacity_factors(rt, data["capacity_factors"])
        if data.get("process_capacity"):
            save_process_capacity_csv(rt, data["process_capacity"])
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 400
    return jsonify({"status": "success"})


@app.route("/api/monthly-inputs/ensure", methods=["POST"])
def api_monthly_inputs_ensure():
    return jsonify(ensure_monthly_grids(runtime_dir()))


@app.route("/api/monthly-inputs/formula", methods=["GET"])
def api_monthly_inputs_formula():
    try:
        ton = float(request.args.get("ton_day", 10.0) or 10.0)
    except (TypeError, ValueError):
        ton = 10.0
    fs = float(request.args.get("f_status", 1.0) or 1.0)
    ps = float(request.args.get("p_status", 1.0) or 1.0)
    cf = float(request.args.get("cap_factor", 1.0) or 1.0)
    return jsonify(explain_capacity_monthly_kg(ton, fs, ps, cf))


@app.route("/api/monthly-pipeline/run", methods=["POST"])
def api_monthly_pipeline_run():
    from pipeline.monthly import run_monthly_pipeline

    data = request.get_json(force=True, silent=True) or {}
    period = (data.get("period") or "").strip()
    if not period:
        return jsonify({"status": "failed", "error": "period (YYYY-MM) gerekli"}), 400
    try:
        out = run_monthly_pipeline(period, triggered_by="api_monthly_ui")
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500
    code = 200 if out.get("status") == "success" else 500
    return jsonify(out), code


@app.route("/api/simulation/baseline/<period>")
def api_simulation_baseline(period: str):
    return jsonify(load_simulation_baseline(period))


@app.route("/api/simulation/run", methods=["POST"])
def api_simulation_run():
    from pipeline.digital_twin import run_digital_twin_simulation

    data = request.get_json(force=True, silent=True) or {}
    base_period = (data.get("period") or "").strip()
    if not base_period:
        return jsonify({"status": "failed", "error": "period (YYYY-MM) gerekli"}), 400
    payload = {
        "factory_activity": data.get("factory_activity") or {},
        "process_capacity_mult": data.get("process_capacity_mult") or {},
        "process_accept_mult": data.get("process_accept_mult") or {},
        "global_capacity_mult": float(data.get("global_capacity_mult", 1.0) or 1.0),
        "global_waste_mult": float(data.get("global_waste_mult", 1.0) or 1.0),
    }
    try:
        out = run_digital_twin_simulation(base_period, payload)
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500
    code = 200 if out.get("status") == "success" else 500
    return jsonify(out), code


@app.route("/api/network/<period>")
def api_network(period: str):
    source = request.args.get("source", "matches_lca")
    if source not in ("matches_lca", "selected"):
        source = "matches_lca"
    return jsonify(build_network_payload(period, source=source))


@app.route("/api/periods")
def api_periods():
    return jsonify({"periods": list_periods_from_runtime()})


@app.route("/pipeline")
def pipeline_page():
    rt = runtime_dir()
    files_info: list[dict] = []
    seen: set[str] = set()
    if rt.is_dir():
        core = [
            "factories.xlsx",
            "processes.xlsx",
            "waste_streams.xlsx",
            "waste_process_links.xlsx",
            "matches_LCA_ready.xlsx",
            "ewc_nace_map.csv",
            "process_capacity.csv",
            "selected_matches.csv",
        ]
        for name in core:
            p = rt / name
            files_info.append(
                {
                    "name": name,
                    "exists": p.is_file(),
                }
            )
            seen.add(name)
        for p in sorted(rt.glob("matches_LCA_*.xlsx")):
            if p.name in seen:
                continue
            if "eski" in p.name.lower():
                continue
            files_info.append({"name": p.name, "exists": True})
    return render_template("pipeline.html", runtime=str(rt), files_info=files_info)


@app.route("/api/network_graph/<period>")
def api_network_graph_html(period: str):
    """PyVis ile süreç/atık/fabrika düğümleri (isteğe bağlı bağımlılık)."""
    source = request.args.get("source", "matches_lca")
    if source not in ("matches_lca", "selected"):
        source = "matches_lca"
    try:
        import networkx as nx
        from pyvis.network import Network
    except ImportError:
        return (
            "<html><body style='background:#0F172A;color:#94A3B8;font-family:Inter;padding:24px;'>"
            "<p>PyVis / NetworkX yüklü değil. Kurulum: <code>pip install pyvis networkx</code></p></body></html>"
        )

    from web.data_access import augment_factories_for_used_ids, load_factories_map

    df, err = load_matches_for_network(period, source=source)
    if err or df.empty:
        return f"<html><body style='background:#0F172A;color:#E2E8F0;padding:24px;'>Veri yok: {err or 'boş'}</body></html>"

    used_ids: set[int] = set()
    for _, row in df.iterrows():
        sf = parse_factory_id(row["source_factory"])
        tf = parse_factory_id(row["target_factory"])
        if sf is not None:
            used_ids.add(sf)
        if tf is not None:
            used_ids.add(tf)
    factories, _ = augment_factories_for_used_ids(load_factories_map(), used_ids)
    G = nx.MultiDiGraph()
    wcol = "waste_amount_monthly" if "waste_amount_monthly" in df.columns else (
        "waste_amount_base" if "waste_amount_base" in df.columns else None
    )
    for i, (_, row) in enumerate(df.iterrows()):
        sf = parse_factory_id(row["source_factory"])
        tf = parse_factory_id(row["target_factory"])
        if sf is None or tf is None:
            continue
        w = float(pd.to_numeric(row[wcol], errors="coerce") or 0.0) if wcol else 0.0
        sn = factories.get(sf, {}).get("name", f"Tesis {sf}")
        tn = factories.get(tf, {}).get("name", f"Tesis {tf}")
        G.add_node(f"F{sf}", label=str(sn)[:32], color="#3B82F6", shape="box")
        G.add_node(f"F{tf}", label=str(tn)[:32], color="#10B981", shape="box")
        wid = row.get("waste_id") if "waste_id" in df.columns else ""
        mid = row.get("match_id") if "match_id" in df.columns else i
        label = f"{w/1000:.2f}t" if w else "—"
        G.add_edge(
            f"F{sf}",
            f"F{tf}",
            key=i,
            label=label,
            title=f"match {mid} · waste {wid} · {w:.0f} kg",
        )

    net = Network(
        height="640px",
        width="100%",
        directed=True,
        bgcolor="#0F172A",
        font_color="#E2E8F0",
    )
    net.from_nx(G)
    net.repulsion(
        node_distance=200,
        central_gravity=0.15,
        spring_length=160,
        spring_strength=0.06,
        damping=0.88,
    )
    return net.generate_html()


def main():
    app.run(host="127.0.0.1", port=5050, debug=True)


if __name__ == "__main__":
    main()
