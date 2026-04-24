# pipeline

Workflow orchestration layer for monthly runs, scenarios, and simulation.

## Responsibilities

- monthly pipeline execution
- scenario pipeline execution
- digital twin style simulation helpers
- exporting selected results

## Key Files

- `monthly.py`: main monthly orchestration
- `scenario.py`: scenario-based reruns and constraints
- `digital_twin.py`: simulation-oriented adjustments
- `selected_export.py`: selected output export helpers

## Inputs

Reads reference and runtime data from `outputs/runtime/` and shared logic from `core/`.

## Outputs

Writes generated match, capacity, and selection files back to `outputs/runtime/`.
