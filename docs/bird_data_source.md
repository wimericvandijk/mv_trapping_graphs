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

## Access Options

Two realistic access options are:

1. Private Google Sheets API access using a service account.
2. A controlled private export process into a private raw-data file.

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
