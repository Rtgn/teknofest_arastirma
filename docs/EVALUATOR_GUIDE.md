# Evaluator Guide

This guide is for competition evaluators who want to understand the project quickly without reading the full codebase.

## Project Purpose

The project supports industrial symbiosis analysis at OSB scale. It helps identify which waste streams from one factory can be used by another process, estimates environmental and economic impact, and selects the best feasible set of matches through optimization.

## Core Value

The system combines four layers in one workflow:

1. Structured industrial input data
2. LCA-based impact estimation
3. Composite scoring
4. Optimization-based selection

This makes the output more explainable than a simple rule-based matching list.

## What Is In The Zip

The repository is divided into clear modules:

- `app/`: user interface and local API layer
- `core/`: business rules and reusable logic
- `pipeline/`: monthly and scenario workflows
- `services/lca/`: local LCA logic and lightweight SQLite-backed profiles/factors
- `services/reporter/`: report-generation utilities
- `data_schemas/templates/`: input templates
- `outputs/runtime/`: generated working files

See [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) for the full map.

## Recommended Review Path

If you only have a few minutes, review in this order:

1. [`../README.md`](../README.md)
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`../app/README.md`](../app/README.md)
4. [`../pipeline/README.md`](../pipeline/README.md)
5. [`../services/README.md`](../services/README.md)

## End-To-End Flow

1. Reference files are placed in `outputs/runtime/`.
2. The monthly pipeline builds candidate matches.
3. The LCA service computes impact metrics for each candidate.
4. Scoring combines environmental and economic dimensions.
5. Optimization chooses a feasible subset of matches.
6. Results are written back to `outputs/runtime/` and can be explored in the Flask UI.

## Main Inputs

Typical required inputs include:

- `factories.xlsx`
- `processes.xlsx`
- `waste_streams.xlsx`
- `waste_process_links.xlsx`
- `process_capacity.csv`
- supporting templates such as resource use, emission factors, and monthly status files

The input schema definitions are documented in [`../data_schemas/README.md`](../data_schemas/README.md).

## Main Outputs

Important generated outputs include:

- `matches_LCA_{YYYY-MM}.xlsx`
- `process_capacity_monthly_{YYYY-MM}.xlsx`
- `selected_matches_{YYYY-MM}.xlsx`
- optimization support artifacts written during runs

## How To Run A Basic Demo

```bash
pip install -r requirements.txt
pip install -r app/requirements.txt
python -m app.app
```

Open `http://127.0.0.1:5050`.

## Explainability Notes

The project is explainable because:

- the data contracts are visible in Excel/CSV templates
- the LCA calculation logic is implemented in readable Python code
- the architecture separates concerns by folder
- runtime inputs and outputs are kept in a dedicated directory
- optimization is a final selection layer, not a black box replacing the full pipeline

## Known Boundaries

- GAMS execution depends on local availability of the GAMS executable.
- Some workflows expect prepared runtime files in `outputs/runtime/`.
- The lightweight SQLite layer is used for LCA profiles and factors, while the main application data still uses Excel/CSV runtime files.
