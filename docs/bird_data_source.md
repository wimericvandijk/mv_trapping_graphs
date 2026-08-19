# Bird Data Source

This document records the current understanding of the bird-sightings source and the privacy rules that should govern any future integration.

## Source

- Current source: Google Sheet under project-controlled Google Drive
- Access status: controlled by the project
- Intended use: future dashboard integration

## Current Observed Columns

The current sheet appears to include at least these columns:

- `Timestamp`
- `Email Address`
- `Name`
- `Date observed`
- `Nearest Trap`
- `Comments`
- `Bird Species`

`Bird Species` will require normalization or categorisation before it is suitable for stable dashboard use.

## Privacy Classification

Treat the Google Sheet as a private raw source.

These columns must not be published directly:

- `Timestamp`
- `Email Address`
- `Name`

These columns require caution:

- `Comments`

`Comments` should be treated as private by default because free-text fields may contain names, contact details, or other identifying information.

## First Public Whitelist

The first public-safe bird dataset should include only fields that are clearly needed for dashboard use.

Recommended starting whitelist:

- `date_observed`
- `nearest_trap`
- `bird_species`

Current decision:

- `nearest_trap` is considered safe for public viewing
- it is still unlikely to be shown on the public webpage in the near term
- `bird_species` should be normalized into a controlled dashboard species model rather than treated as unrestricted free text

Recommended default exclusions from public outputs:

- `timestamp`
- `email_address`
- `name`
- `comments`

## Recommended Ingestion Shape

The Google Sheet should not be published as a public raw CSV while it contains personal data.

Recommended approach:

1. Read the sheet through a private access path.
2. Save the raw extract only in a private raw-data location.
3. Apply an explicit public whitelist during transform.
4. Publish only the filtered bird dataset or derived bird aggregates.

Current temporary approach:

1. Manually download the current Google Sheet responses as a private `.xlsx` file.
2. Save that workbook under `data/raw`, currently as `Observed Birds (Responses).xlsx`.
3. Let the publish step read that local private workbook directly.
4. Replace this manual workbook step with Google Sheets API access as soon as practical.

Current API implementation shape:

1. Use `scripts/import/import_bird_sightings.py` as the dedicated Google Sheets import step.
2. Authenticate with a Google service account that has access to the private sheet.
3. Read a specific A1 range through the Google Sheets API `spreadsheets.values.get` JSON path.
4. Save the fetched rows into a private raw CSV under `data/raw`, currently `bird-sightings-api.csv` by default.
5. Keep remote sheet access out of the publish step itself.

## First Implementation Status

The current codebase now supports an initial private bird-data publish path.

- `scripts/publish/publish_to_json.py` currently reads private bird exports from either `data/raw/bird-sightings*.csv` or `data/raw/Observed Birds*.xlsx`
- the current working path is a manually downloaded private workbook, `data/raw/Observed Birds (Responses).xlsx`
- `scripts/import/import_bird_sightings.py` now exists for the Google Sheets API path and can write a private raw CSV for the publish step to consume
- the current parser reads `Date observed` and `Bird Species` columns, or their snake_case equivalents
- only normalized `South Island Robin` observations are currently published into the dashboard species list
- the dashboard displays that species as `SI Robin`, while keeping the underlying data key as `South Island Robin`
- the trap-catch aggregate is displayed as `All Pest Species`, and bird observations are intentionally excluded from that aggregate
- raw bird exports remain private under `data/raw` and are not copied into public outputs
- dashboard metadata now marks bird species with `observations` wording rather than `catches`
- dashboard metadata now also marks bird species as non-pest so they can be styled differently in the selector

This keeps the first bird integration narrow and privacy-safe while leaving room for broader species support later.

## Access Options

Two realistic access options are:

1. Private Google Sheets API access using a service account.
2. A controlled private export process into a private raw-data file.

Current preference:

- keep the manual private `.xlsx` download only as a short-term bridge
- move to Google Sheets API access soon so the private workbook step can be retired
- keep the dedicated importer responsible for remote access and keep the publisher responsible only for local private files

Public Google Sheet publishing is not recommended for the current sheet while personal fields remain present.

## Open Design Questions

Before implementation, decide:

1. Whether the publish layer should output bird-specific JSON files or merge bird data into existing site data structures.
2. Whether `comments` need any sanitized derived form later, or should remain private permanently.

## Current Integration Decisions

- Bird sightings fit reasonably well into the current species selector and display model.
- Bird sighting counts are expected to be sparse, so charts and summaries should tolerate low-volume data without implying smooth trends.
- `nearest_trap` can remain in the public-safe filtered dataset even if it is not initially rendered in the public UI.
- At the current stage, the only consistently counted bird species is South Island Robin.
- A sensible first implementation can therefore focus on South Island Robin while leaving room for a broader bird-species model later.
- The current unresolved step is wiring the Google Sheets API importer to live credentials and a stable sheet range so the manual `.xlsx` bridge can be retired.
