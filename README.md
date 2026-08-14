# Marsden Valley Trapping Dashboard

This repository is building a public trapping dashboard from Trap.NZ data for the Marsden Valley Trapping Group.

## Current Capability

The project currently has a working transform and publish pipeline.

- Reads Trap.NZ raw CSV exports from `data/raw`.
- Joins trap records with trap metadata.
- Normalizes species and trap type names from raw source values.
- Applies data-cleansing business rules before publication.
- Keeps only the last report for the same trap on the same day.
- Flags invalid records into a separate review file.
- Writes annual cleaned CSV outputs and a combined `all_data.csv` into `data/published/annual`.
- Loads trap/species validation policy from `config/trap_species_rules.json`.
- Publishes dashboard JSON files into `site/data` from the annual cleaned CSV files.
- Reuses a shared script logging helper across script entry points.

## Current Outputs

The main outputs from `scripts/transform/annualise_csv.py` are:

- `data/published/annual/all_project_data_<year>.csv`
- `data/published/annual/all_project_data_<year>_to_<date>.csv` for partial years
- `data/published/annual/all_data.csv`
- `data/published/annual/invalid_records.csv`

The main outputs from `scripts/publish/publish_to_json.py` are:

- `site/data/metadata.json`
- `site/data/weekly.json`
- `site/data/yearly_comparison.json`
- `site/data/summary.json`

`invalid_records.csv` currently records two review cases:

- `wrong trap type`
- `overwritten`

## Current Project State

The data-cleaning, annualisation, and first JSON publish stage are working.

The next major step is to build the first proof-of-concept dashboard page in `site` against the published JSON files.

## Main Files

- `scripts/transform/annualise_csv.py`: active raw CSV ingestion and cleansing pipeline
- `scripts/transform/process_cleansed_files.py`: stub for the later processed-data or parquet stage
- `scripts/transform/domain_constants.py`: canonical species and trap type names shared by Python scripts
- `scripts/publish/publish_to_json.py`: site JSON publisher from annual cleaned CSV files
- `scripts/script_logging.py`: shared logging setup used by script entry points
- `config/trap_species_rules.json`: trap/species policy rules
- `config/README.md`: explanation of the rules file
- `docs/site_data_formats.md`: JSON contract for the published site data
- `backlog.md`: planned next work

## Running The Current Pipeline

From the repository root:

```powershell
python scripts/transform/annualise_csv.py
python scripts/publish/publish_to_json.py
```

## Intended Direction

The target architecture remains a static public website, hosted on GitHub Pages, with scheduled data refreshes via GitHub Actions and browser-based charts reading published summary data.