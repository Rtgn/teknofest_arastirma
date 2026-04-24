# outputs/runtime

Runtime exchange directory for local runs.

## Purpose

This folder is where the application reads working input files from and writes generated output files to.

## Typical Inputs

- `factories.xlsx`
- `processes.xlsx`
- `waste_streams.xlsx`
- `waste_process_links.xlsx`
- `process_capacity.csv`
- monthly status and capacity factor files

## Typical Outputs

- `matches_LCA_{YYYY-MM}.xlsx`
- `process_capacity_monthly_{YYYY-MM}.xlsx`
- `selected_matches_{YYYY-MM}.xlsx`

## Notes

- this folder is intentionally ignored in git except for this README
- evaluators can inspect this folder after a run to understand the system’s concrete inputs and outputs
