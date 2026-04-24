# teknofest_arastirma

Industrial symbiosis decision-support system for Organized Industrial Zones (OSB). The repository combines data preparation, LCA-based environmental and economic scoring, optimization, and a Flask interface in one package.

This project is organized to be understandable for both technical reviewers and competition evaluators:

- Start here: [`docs/EVALUATOR_GUIDE.md`](docs/EVALUATOR_GUIDE.md)
- Technical architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Folder map: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- Runtime input/output conventions: [`outputs/runtime/README.md`](outputs/runtime/README.md)

## What The System Does

At a high level, the system:

1. Reads factory, process, waste, and capacity data from Excel/CSV files.
2. Builds monthly industrial symbiosis match candidates.
3. Computes LCA-based impact metrics such as avoided emissions, processing burden, transport burden, and profit.
4. Scores candidate matches.
5. Runs optimization to select the best feasible set of matches.
6. Exposes the workflow through a local Flask application and utility APIs.

## Main Folders

- [`app/`](app/README.md): Flask UI and HTTP endpoints
- [`core/`](core/README.md): shared business logic and contracts
- [`pipeline/`](pipeline/README.md): monthly and scenario orchestration
- [`services/`](services/README.md): internal LCA and reporting services
- [`data_schemas/`](data_schemas/README.md): input templates and data contracts
- [`outputs/runtime/`](outputs/runtime/README.md): generated runtime artifacts

## Quick Start

```bash
pip install -r requirements.txt
python -m app.app
```

Open: `http://127.0.0.1:5050`

## Minimal Demo Flow

1. Put the required Excel/CSV files into `outputs/runtime/`.
2. Start the Flask app with `python -m app.app`.
3. Open the dashboard in the browser.
4. Use the monthly data and pipeline pages to prepare inputs and run a monthly pipeline.
5. Inspect generated files in `outputs/runtime/`, especially:
   - `matches_LCA_{YYYY-MM}.xlsx`
   - `process_capacity_monthly_{YYYY-MM}.xlsx`
   - `selected_matches_{YYYY-MM}.xlsx`

## Running The Monthly Pipeline

The application expects its working directory to be the repository root. Runtime files are read from and written to `outputs/runtime/`.

If the required reference files are present, the monthly pipeline can be triggered from the UI or programmatically from the `pipeline` package.

## Scenario Runs

Scenario analysis builds on an existing monthly run and applies modified waste or capacity conditions before re-running scoring and optimization.

Example:

```python
from pipeline.scenario import ScenarioWasteBounds, run_scenario_pipeline

run_scenario_pipeline(
    1,
    "2026-05",
    waste_bounds=ScenarioWasteBounds(global_max_kg_month=1e6),
)
```

## Configuration

| Variable | Meaning |
|---|---|
| `LCA_API_URL` / `LCA_SERVICE_URL` | LCA base URL; defaults to the local Flask app at `/api/lca` |
| `GAMS_EXE` | Absolute path to `gams.exe` if GAMS is used |
| `USE_MOCK_LCA` | `1` uses a mock LCA path instead of HTTP |

The main path settings are defined in `core.config`, including `RUNTIME_DIR = outputs/runtime`.

## What Reviewers Should Inspect First

- `docs/EVALUATOR_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `app/app.py`
- `pipeline/monthly.py`
- `services/lca/calculator.py`

## Packaging Notes

When sharing this repository as a zip:

- exclude `.venv/`
- exclude `__pycache__/`
- exclude large temporary outputs unless they are part of the demo
- include a small representative sample of runtime inputs or outputs if reviewers need a reproducible walkthrough
