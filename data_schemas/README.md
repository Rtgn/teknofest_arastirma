# data_schemas

Input templates and schema contracts for the project.

## Purpose

This folder makes the project explainable at the data level. Reviewers can inspect the templates and documentation to understand what the application expects before looking at the code.

## Contents

- `templates/`: Excel and CSV templates used as reference inputs
- `column_dictionary.md`: column-level documentation

## Typical Templates

- factory definitions
- process definitions
- waste stream definitions
- waste-process links
- resource use and emission factors
- capacity and monthly status inputs
- BREF-related metadata and limits

## Why It Matters

The project’s main inputs are not hidden inside code. They are represented explicitly as template files and documented here.
