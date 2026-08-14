# Backlog

This file tracks the current plan for the trapping dashboard project.

## Done

- Repository structure established.
- Historical raw Trap.NZ CSV exports are present in `data/raw`.
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

## Next

1. Review and collect feedback on the current dashboard slice.
2. Investigate how much dashboard state should be persisted across interactions.
3. Add operational views once trap-line level summaries exist.

## After That

1. Use the working examples in `config/secrets.json` as the starting point for Trap.NZ API integration.
2. Optimise those API calls for regular scheduled use.
3. Replace or complement CSV ingestion with automated API ingestion.
4. Add GitHub Actions for scheduled nightly processing.
5. Prepare GitHub Pages hosting flow.

## Later Analytics

1. Analyse by trap line.
2. Compare catches per trap.
3. Compare catches per visit.
4. Investigate rebait frequency.
5. Support operational decision-making views.

## Notes

- The Word planning document is in `docs/Trapping_Dashboard_Project_Summary_v2.docx`.
- Current review URL: `https://wimericvandijk.github.io/mv_trapping_graphs/`
- The current implementation is ahead of the original plan in one area: the cleansing rules and invalid-record review flow are already in place.
- The biggest missing pieces are now dashboard polish and the next layer of analytics rather than the initial data publish or page scaffold.
- The publish layer should use annual cleaned CSV files as input; `all_data.csv` is a convenience output rather than the preferred working source.
- `site/data` is already the publish target for generated dashboard JSON. Parquet belongs to the later processed-data layer, not this publish target.