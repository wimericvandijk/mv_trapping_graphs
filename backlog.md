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
- The weekly chart period selector now supports ordered rolling 3, 6, and 12 month options followed by available years.
- The period selector has been restyled as a clearer clickable control.
- A project-information panel is now available from a button in the page header, using public content from `config/site_project.json` and markdown content from `docs/project_about.md`.
- A cross-repository publish workflow now exists for a development-repository to public-site repository split and now republishes the public site from pushes to `main`.
- The public site is now published from `MarsdenValleyTrappers/trapping_graphs` at `https://marsdenvalleytrappers.github.io/trapping_graphs/`.
- The private development repo can now publish to the public repo using `PUBLIC_SITE_DEPLOY_TOKEN`, currently backed by a classic PAT from the `MarsdenValley` GitHub user.
- The all-years comparison chart supports year toggles and expand or close behavior.
- Summary trends now support year-on-year comparisons for annual periods and same-season comparisons for the rolling 6-month view.
- The publish step can now optionally merge a private bird-sightings CSV export into the dashboard species options, starting with South Island Robin observations.
- A dedicated `scripts/import/import_bird_sightings.py` script now exists for the Google Sheets API path and can write a private raw bird CSV for the publish step.
- The species selector now distinguishes pest and non-pest species, displays `All Pest Species` for the pest aggregate, and displays `SI Robin` for South Island Robin.
- The current dashboard layout, chart expansion behavior, and trend logic are good enough for review.

## Planned Work

1. Replace the current manual private `.xlsx` bird download with direct Google Sheets API access so the bird source can refresh into the publish path without a manual export step.
   Implementation shape:
   - create a dedicated bird import script under `scripts/import/import_bird_sightings.py`
   - authenticate with a Google service account that has been granted access to the private sheet
   - read a specific sheet range through the Google Sheets API `spreadsheets.values.get` JSON path
   - write the fetched rows into a private raw CSV under `data/raw`
   - keep publish logic in `scripts/publish/publish_to_json.py` and keep remote API access out of the publish step
   - optionally allow the bird import script to run the publish step after a successful fetch
2. Add a separate infrequent full Trap.NZ refresh workflow, perhaps every 3 months, scheduled separately from the nightly recent-refresh workflow, for example around 11:30 UTC.
3. Investigate a less awkward git flow for automated site-data commits versus manual code changes on `main`, because the nightly refresh commits can force local rebases and make normal pushes brittle.
4. Add source-specific stale-data tolerance in published metadata and site messaging, for example around 7 days for Trap.NZ data and 21 days for bird sightings, so slower-moving bird data does not make the whole dashboard look stale.

## Bird Data Notes

- The current bird-sightings source is a Google Sheet under project-controlled Google Drive.
- The sheet includes personal fields such as `Email Address` and `Name`, so the raw sheet must be treated as a private source.
- `Comments` should also be treated as private by default because free-text may contain identifying information.
- The first public bird dataset should likely whitelist only `date_observed`, `nearest_trap`, and `bird_species`.
- `nearest_trap` is considered public-safe, even if it is not likely to be shown on the public webpage soon.
- `bird_species` will need some normalization or categorisation before bird data is stable enough for dashboard use.
- At this stage, the only bird species that appears to be counted consistently is South Island Robin.
- Bird sightings fit the current species-selector and display model better than a separate dashboard section.
- Bird data is expected to be sparse, so any charts or summaries need to handle low-volume observations cleanly.
- Future implementation should use a private ingestion path and publish only filtered bird outputs.
- The current temporary workflow uses a manually downloaded private `.xlsx` file under `data/raw`.
- The current first implementation only publishes normalized South Island Robin observations when a private bird export file is present.
- The preferred near-term improvement is to move from the manual workbook bridge to the new Google Sheets API importer.
- See `docs/bird_data_source.md` for the current source contract and privacy rules.

## Later Analytics

1. Analyse by trap line.
2. Compare catches per trap.
3. Compare catches per visit.
4. Investigate rebait frequency.
5. Support operational decision-making views.
6. Add operational views once trap-line level summaries exist.

## Notes

- The Word planning document is in `docs/Trapping_Dashboard_Project_Summary_v2.docx`.
- Current public URL: `https://marsdenvalleytrappers.github.io/trapping_graphs/`
- This repository should not publish its own GitHub Pages URL, including `https://wimericvandijk.github.io/mv_trapping_graphs/`.
- The classic PAT previously used from another account can be revoked once `PUBLIC_SITE_DEPLOY_TOKEN` has been replaced and a publish run has succeeded.
- The current implementation is ahead of the original plan in one area: the cleansing rules and invalid-record review flow are already in place.
- The biggest missing pieces are now dashboard polish and the next layer of analytics rather than the initial data publish or page scaffold.
- The publish layer should use annual cleaned CSV files as input; `all_data.csv` is a convenience output rather than the preferred working source.
- `site/data` is already the publish target for generated dashboard JSON. Parquet belongs to the later processed-data layer, not this publish target.
- Initial review feedback received so far is positive, but it does not yet identify specific changes or defects.
- More specific review feedback may take time to arrive and may never arrive.
- Dashboard state persistence is not currently defined as a concrete requirement.
