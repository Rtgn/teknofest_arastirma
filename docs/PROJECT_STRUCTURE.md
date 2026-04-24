# Project Structure

This file provides a fast map of the repository for reviewers.

```text
teknofest_arastirma/
├── app/                 Flask UI and local HTTP endpoints
├── core/                Shared business rules, config, parsing, scoring
├── data_schemas/        Input templates and column contracts
├── docs/                Architecture and evaluator-facing documentation
├── optimization/        GAMS/optimization integration and result readers
├── outputs/
│   └── runtime/         Runtime inputs and generated outputs
├── pipeline/            Monthly and scenario orchestration
├── services/
│   ├── lca/             Local LCA service logic and SQLite models
│   └── reporter/        Reporting utilities and prompts
└── utils/               One-off helper scripts and builders
```

## Folder Responsibilities

### `app/`

Contains the Flask entrypoint, templates, static assets, and UI-facing data access helpers.

### `core/`

Contains reusable domain logic such as config, scoring, period handling, ID parsing, LCA client contracts, and data preparation helpers.

### `pipeline/`

Contains the orchestration logic for monthly runs, scenario runs, digital twin simulation, and exporting selected outputs.

### `services/`

Contains internal services:

- `lca/`: local lifecycle assessment calculations and profile/factor persistence
- `reporter/`: report generation logic and prompt templates

### `optimization/`

Contains builders and readers around optimization, including GAMS-oriented CSV preparation and result extraction.

### `data_schemas/`

Contains Excel/CSV templates and schema-level documentation so the inputs remain explicit and reviewable.

### `outputs/runtime/`

Contains the working files used and produced during local runs. This is the main runtime exchange point for the app and pipeline.

### `docs/`

Contains reviewer-facing explanations so the codebase can be understood without deep source inspection.

### `utils/`

Contains small helper scripts that are useful during development or data preparation but are not part of the main application flow.
