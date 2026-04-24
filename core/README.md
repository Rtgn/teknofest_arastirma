# core

Shared business logic and application-wide contracts.

## Responsibilities

- configuration and environment variables
- period parsing and file naming
- ID parsing and normalization
- scoring and derived metrics
- LCA client integration
- data cleaning and matching support

## Key Files

- `config.py`: path and environment configuration
- `period.py`: period parsing and filename helpers
- `scoring.py`: sustainability scoring logic
- `lca_client.py`: LCA request/response integration
- `factory_ids.py`: factory ID normalization

## Used By

- `app/`
- `pipeline/`
- `services/`
- `optimization/`
