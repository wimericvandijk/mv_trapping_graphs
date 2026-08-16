# Marsden Valley Trapping Dashboard

This repository is building a public trapping dashboard from Trap.NZ data for the Marsden Valley Trapping Group.

## Current Capability

The project currently has a working transform and publish pipeline.

- Imports Trap.NZ CSV exports using a local ignored secrets file or environment variables.
- Supports a recent-only Trap.NZ refresh path for scheduled use, followed by annual merge and JSON publish.
- Reads Trap.NZ raw CSV exports from `data/raw`.
- Joins trap records with trap metadata.
- Normalizes species and trap type names from raw source values.
- Applies data-cleansing business rules before publication.
- Keeps only the last report for the same trap on the same day.
- Publishes privacy-filtered annual CSV outputs using an explicit public column whitelist.
- Writes public annual CSV outputs and a combined `all_data.csv` into `data/published/annual`.
- Writes detailed invalid review rows into `data/review/annual`.
- Loads trap/species validation policy from `config/trap_species_rules.json`.
- Publishes dashboard JSON files into `site/data` from the annual cleaned CSV files.
- Reuses a shared script logging helper across script entry points.
- Includes a working static dashboard in `site` with species navigation, an ordered rolling-period and year control, weekly bars, all-years comparison lines, chart expand or close controls, and a project-information panel.

## Current Outputs

The main outputs from `scripts/transform/annualise_csv.py` are:

- `data/published/annual/all_project_data_<year>.csv`
- `data/published/annual/all_project_data_<year>_to_<date>.csv` for partial years
- `data/published/annual/all_data.csv`
- `data/published/annual/invalid_records.csv`
- `data/review/annual/invalid_records.csv`

The main script for importing raw Trap.NZ CSV files is:

- `scripts/import/import_trapnz_csv.py`

The main outputs from `scripts/publish/publish_to_json.py` are:

- `site/data/metadata.json`
- `site/data/weekly.json`
- `site/data/yearly_comparison.json`
- `site/data/summary.json`

`metadata.json` now also carries public project information sourced from `config/site_project.json`, including markdown-backed about content from `docs/project_about.md`.

`invalid_records.csv` currently records two review cases:

- `wrong trap type`
- `overwritten`

The public CSV outputs in `data/published/annual` now keep only these fields:

- `project`
- `record_date`
- `trap_type`
- `strikes`
- `species_caught`
- `clean_datestamp`
- `clean_rule_status`
- `rule_broken`
- `clean_rule_reason`

The detailed internal review CSV under `data/review/annual` retains the broader cleaned row needed for operational review.

## Current Project State

The data-cleaning, annualisation, JSON publish stage, and first dashboard UI are working.

The current dashboard now supports these period options in order:

- `Last 3 months`
- `Last 6 months`
- `Last 12 months`
- calendar years from oldest to most recent available year

The next major step is to refine dashboard behavior, visual polish, and analytics semantics rather than to create the first page from scratch.

## Main Files

- `scripts/transform/annualise_csv.py`: active raw CSV ingestion and cleansing pipeline
- `scripts/import/import_trapnz_csv.py`: Trap.NZ CSV importer using ignored local secrets or environment variables
- `scripts/transform/process_cleansed_files.py`: stub for the later processed-data or parquet stage
- `scripts/transform/domain_constants.py`: canonical species and trap type names shared by Python scripts
- `scripts/publish/publish_to_json.py`: site JSON publisher from annual cleaned CSV files
- `scripts/script_logging.py`: shared logging setup used by script entry points
- `site/index.html`: dashboard structure
- `site/style.css`: dashboard styling
- `site/app.js`: dashboard client-side behavior and chart rendering
- `config/site_project.json`: public project name and about-text source for published site metadata
- `docs/project_about.md`: markdown content source for the project-information panel
- `config/trap_species_rules.json`: trap/species policy rules
- `config/README.md`: explanation of the rules file
- `docs/site_data_formats.md`: JSON contract for the published site data
- `backlog.md`: planned next work

## Running The Current Pipeline

Set up Trap.NZ import credentials first:

- Copy `config/secrets.example.json` to `config/secrets.json` and fill in the real values, or
- Set `TRAPNZ_API_KEY` and `TRAPNZ_PROJECT_ID` in your local environment.

The importer prefers environment variables when both are present. `config/secrets.json` is ignored by git and should never be committed.

From the repository root:

```powershell
python scripts/import/import_trapnz_csv.py
python scripts/transform/annualise_csv.py
python scripts/publish/publish_to_json.py
powershell -ExecutionPolicy Bypass -File scripts/publish/run_dashboard_server.ps1
```

Useful import commands:

```powershell
python scripts/import/import_trapnz_csv.py --list-queries
python scripts/import/import_trapnz_csv.py --dry-run
python scripts/import/import_trapnz_csv.py --no-import --merge-recent --publish
python scripts/import/import_trapnz_csv.py -q all_records
python scripts/import/import_trapnz_csv.py --merge-recent --publish
```

Recommended scheduled refresh command:

```powershell
python scripts/import/import_trapnz_csv.py --merge-recent --publish
```

That path:

- downloads `trap_list` and `recent_records`
- merges only the impacted year data into the existing annual outputs
- republishes the site JSON without forcing a full raw-data rebuild

For development or testing, `--no-import` skips Trap.NZ API calls while still allowing the merge and publish follow-up steps to run against files already present under `data/raw`.

The normal full rebuild path in `scripts/transform/annualise_csv.py` now ignores `*trap-records-recent*.csv` files so the rolling recent import does not create duplicate overwrite rows during a complete rebuild.

The current Python import, transform, and publish scripts are intentionally single-threaded. At the current project scale they are fast enough for regular use, so the implementation currently favors simpler sequential behavior over added concurrency or parallel execution complexity.

## GitHub Actions

The repository now includes a nightly refresh workflow at `.github/workflows/nightly-update.yml`.

It also now includes an optional cross-repository publish workflow at `.github/workflows/publish-public-site.yml` for a private-development to public-site setup.

It requires these repository secrets:

- `TRAPNZ_API_KEY`
- `TRAPNZ_PROJECT_ID`
- `PUBLIC_SITE_DEPLOY_TOKEN` for cross-repository publish to a public site repo

It requires these repository variables for cross-repository publish:

- `PUBLIC_SITE_REPO`, set this to `MarsdenValleyTrappers/trapping_graphs`
- `PUBLIC_SITE_BRANCH`, usually `main`

Workflow behavior:

- On a runner that already has cached detailed annual review data, it uses the recent-only API refresh path.
- On a cache miss, it bootstraps by importing `all_records`, then runs the full transform and publish steps.
- It commits refreshed `site/data/metadata.json`, `site/data/weekly.json`, `site/data/yearly_comparison.json`, and `site/data/summary.json` back to `main`.
- The existing Pages deploy workflow then publishes the updated site from that push.
- The optional cross-repository publish workflow can instead copy the built `site/` folder into a separate public repository owned by an organisation or another GitHub account.
- It now runs automatically on pushes to `main` and can also be run manually with `workflow_dispatch`.

Recommended private-development to public-site setup:

1. Keep this repository as the private development repository.
2. Use the separate public repository `MarsdenValleyTrappers/trapping_graphs` to hold only the published static site.
3. Create a classic personal access token from the `MarsdenValley` GitHub user or another dedicated automation account that can write to the public repository.
4. Store that token in this private development repository as `PUBLIC_SITE_DEPLOY_TOKEN`.
5. Set `PUBLIC_SITE_REPO` to `MarsdenValleyTrappers/trapping_graphs` and `PUBLIC_SITE_BRANCH` to the target branch, usually `main`.
6. Enable GitHub Pages in the public repository using the published branch root.
7. The `Publish Static Site To Public Repo` workflow can be run manually for testing and now also runs automatically on pushes to `main`.

Current working deployment setup:

- the private development repository runs the publish workflow
- `PUBLIC_SITE_DEPLOY_TOKEN` is currently a classic PAT created from the `MarsdenValley` GitHub user
- that secret is stored in the private repository and is used to push the built `site/` output into `MarsdenValleyTrappers/trapping_graphs`

Token rotation note:

- if an older token from another account is no longer referenced by `PUBLIC_SITE_DEPLOY_TOKEN` and is not used elsewhere, it can be revoked
- the public site remains live if the token expires, but future publish workflow runs will fail until the secret is replaced with a new valid token
- rotate the deployment token before expiry, update `PUBLIC_SITE_DEPLOY_TOKEN`, run the publish workflow once to confirm it still works, then revoke the old token

Troubleshooting:

- If the nightly workflow fails with authentication errors, verify that the repository secrets `TRAPNZ_API_KEY` and `TRAPNZ_PROJECT_ID` are present and current.
- If the recent-only refresh path fails on a new runner, the workflow should fall back to a full bootstrap import on cache miss. Check whether the `data/review/annual` cache restored successfully.
- If the workflow runs but commits no changes, inspect the workflow logs to confirm whether Trap.NZ returned new data and whether the published JSON files actually changed.
- If the workflow commits updated site data but the site does not change, check the `Deploy Dashboard To GitHub Pages` workflow to confirm the subsequent Pages deployment succeeded.
- If the cross-repository publish workflow fails before cloning, verify `PUBLIC_SITE_REPO` and `PUBLIC_SITE_DEPLOY_TOKEN` are configured in the private repository.
- If the cross-repository publish workflow fails to push, verify that the token can write to the target public repository and that the target branch already exists.

## Review URL

The current public site is available at:

- `https://marsdenvalleytrappers.github.io/trapping_graphs/`

The earlier personal review URL was:

- `https://wimericvandijk.github.io/mv_trapping_graphs/`

The organisation-owned public site is now published from `MarsdenValleyTrappers/trapping_graphs` on GitHub Pages.

## Intended Direction

The target architecture remains a static public website, hosted on GitHub Pages, with scheduled data refreshes via GitHub Actions and browser-based charts reading published summary data.
