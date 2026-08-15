# Backlog

This file tracks the current plan for the trapping dashboard project.

## Done

- Repository structure established.
- Historical raw Trap.NZ CSV exports are present in `data/raw`.
- Trap.NZ CSV imports can now run locally using `scripts/import/import_trapnz_csv.py` with ignored local secrets or environment variables.
- Trap.NZ scheduled refreshes can now use a recent-only import path that merges touched annual outputs and republishes site JSON.
- CSV ingestion is now complemented by an end-to-end automated Trap.NZ API path, including live import, recent-year merge, and site publish.
- GitHub Actions can now run scheduled nightly processing with a cached recent-refresh path and a full-import bootstrap fallback.
- Raw trap records can be cleaned and annualised with `scripts/transform/annualise_csv.py`.
- Trap metadata is joined into the cleaned output.
- Species and trap type names are normalized.
- Trap/species business rules are externalized to `config/trap_species_rules.json`.
- Invalid records are separated for review.
- Initial site JSON formats are defined in `docs/site_data_formats.md`.
- A first site publisher now generates JSON into `site/data` from the annual cleaned CSV files.
- Shared logging setup is extracted into `scripts/script_logging.py`.
- A first dashboard page now exists in `site`.
- The all-years comparison chart supports year toggles and expand or close behavior.
- Summary trends now support year-on-year comparisons for annual periods and same-season comparisons for the rolling 6-month view.
- The current dashboard layout, chart expansion behavior, and trend logic are good enough for review.

## Planned Work

1. Prepare GitHub Pages hosting flow.
2. Investigate access to the separate bird-sightings data source and how to integrate bird sightings into the dashboard species options.
3. Add a simple button or menu-triggered project-information panel with basic formatted text and links for project background and contact details.
4. Add a separate infrequent full Trap.NZ refresh workflow, perhaps every 3 months, scheduled separately from the nightly recent-refresh workflow, for example around 11:30 UTC.

## Later Analytics

1. Analyse by trap line.
2. Compare catches per trap.
3. Compare catches per visit.
4. Investigate rebait frequency.
5. Support operational decision-making views.
6. Add operational views once trap-line level summaries exist.

## Notes

- The Word planning document is in `docs/Trapping_Dashboard_Project_Summary_v2.docx`.
- Current review URL: `https://wimericvandijk.github.io/mv_trapping_graphs/`
- The current implementation is ahead of the original plan in one area: the cleansing rules and invalid-record review flow are already in place.
- The biggest missing pieces are now dashboard polish and the next layer of analytics rather than the initial data publish or page scaffold.
- The publish layer should use annual cleaned CSV files as input; `all_data.csv` is a convenience output rather than the preferred working source.
- `site/data` is already the publish target for generated dashboard JSON. Parquet belongs to the later processed-data layer, not this publish target.
- Initial review feedback received so far is positive, but it does not yet identify specific changes or defects.
- More specific review feedback may take time to arrive and may never arrive.
- Dashboard state persistence is not currently defined as a concrete requirement.
