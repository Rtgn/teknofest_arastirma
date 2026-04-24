# optimization

Optimization integration layer.

## Responsibilities

- prepare optimization input tables
- invoke the external optimization workflow
- read selected match results back into the application

## Key Files

- `gdx_builder.py`: prepares optimization-oriented CSV inputs
- `gams_runner.py`: runs GAMS through a subprocess call
- `result_reader.py`: reads selected match outputs
- `gms/`: model files and notes for the GAMS side

## Notes

- this layer is intentionally separated from `core/` so optimization concerns stay isolated
- GAMS availability is an environment prerequisite for the full optimization path
