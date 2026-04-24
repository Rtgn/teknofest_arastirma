# app

Flask application layer for the project.

## Responsibilities

- dashboard and UI pages
- monthly input management endpoints
- simulation endpoints
- pipeline-triggering endpoints
- local LCA HTTP routes

## Key Files

- `app.py`: Flask entrypoint and route definitions
- `data_access.py`: UI-oriented reads from runtime outputs
- `monthly_data_io.py`: monthly input read/write helpers
- `templates/`: Jinja templates for pages
- `static/`: CSS and static assets

## Depends On

- `core/`
- `pipeline/`
- `services/lca/`
- `outputs/runtime/`
