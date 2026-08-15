# Config

## Secrets

`secrets.example.json` shows the expected local shape for Trap.NZ import credentials and query configuration.

- Copy `secrets.example.json` to `secrets.json` locally and replace the placeholder values.
- `secrets.json` is ignored by git and must not be committed.
- `scripts/import/import_trapnz_csv.py` can read credentials from either `secrets.json` or the `TRAPNZ_API_KEY` and `TRAPNZ_PROJECT_ID` environment variables.
- Environment variables take precedence over values in `secrets.json`.

The importer logs a masked request URL using `<API_KEY>` and `<project_id>` placeholders so the query shape remains visible without exposing credentials.

`queries`

- `trap_list`, `recent_records`, and `all_records` are the normal built-in examples.
- Additional query entries may include a `cql_filter` to narrow the Trap.NZ export.
- A query may also use a full `url` instead of `type_name` when a hand-built WFS request is needed.

## Site Project

`site_project.json` holds public project identity and about-text source information for the dashboard site.

- `project_name` is the preferred displayed project name for the site header and published site metadata.
- `about.summary` holds short public descriptive text for the site project-information panel.
- `about.source_path` can point to a fuller source document when the site should reference rather than duplicate the longer project background.

Current usage

- `scripts/publish/publish_to_json.py` reads `site_project.json` and publishes it into `site/data/metadata.json`.
- `site/app.js` reads the published project name from `site/data/metadata.json` rather than relying on hard-coded HTML text.
- The local site shows a header button that opens a project-information panel using the published `project.about` fields.

## Trap Species Rules

`trap_species_rules.json` defines the policy used by `scripts/transform/annualise_csv.py` when deciding whether a catch should be flagged as `wrong trap type`.

`species_collections`

- Optional named groups of species that can be reused elsewhere in the file.
- Example: `Rat` expands to `Rat`, `Rat - Ship`, `Rat - Norway`, and `Rat - Kiore`.
- Example: `Mustelid` expands to `Stoat`, `Weasel`, and `Ferret`.

`restricted_species`

- Only these species or species collections are checked against trap type rules.
- Any species not listed here is treated as permitted in any trap type.

`trap_type_allowed_species`

- Maps each trap type to the species or species collections that are valid for that trap type.
- Entries can use either individual species names such as `Mouse` or collection names such as `Mustelid`.

How the rule is applied

- The script expands collection names first.
- If a caught species is not in `restricted_species`, the record passes this rule.
- If a caught species is in `restricted_species` but not in the trap type's allowed list, a privacy-filtered row is written to `data/published/annual/invalid_records.csv` with `rule_broken=wrong trap type`.
- The corresponding detailed review row is written to `data/review/annual/invalid_records.csv` for internal operational follow-up.

Current usage

- `scripts/transform/annualise_csv.py` uses this file during raw-data cleansing.
- Collection names can be used in both `restricted_species` and `trap_type_allowed_species`.
