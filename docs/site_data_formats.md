# Site Data Formats

This document defines the first published JSON formats for the dashboard site.

The aim is to support the initial dashboard requirements from the project summary document:

- default last 6 months view
- species selection
- period or year selection
- weekly catches for the selected species and period
- same-species all-years comparison
- species totals for the selected period
- summary metrics and trend indicators

## Design Principles

- JSON should be pre-aggregated for the browser.
- Published files should be stable and versioned.
- Public annual CSVs in `data/published/annual` should keep only the privacy-safe fields needed for publication.
- Detailed invalid review rows should be kept separately under `data/review/annual` rather than in public published outputs.
- The publish layer should use the annual cleaned CSV files as its primary input, not `all_data.csv`.
- Site files in `site/data` should only contain the fields needed by the dashboard.
- Species names and trap type names must use canonical values from `domain_constants.py`.

## Proposed Files

The first site data contract should consist of four files:

1. `site/data/metadata.json`
2. `site/data/weekly.json`
3. `site/data/yearly_comparison.json`
4. `site/data/summary.json`

## 1. metadata.json

Purpose:

- describes the published dataset
- carries public project identity and about-text source information from `config/site_project.json`
- tells the site which species and years are available
- supports default filters and labels

Format:

```json
{
  "schema_version": 1,
  "generated_at": "2026-08-14T15:00:00Z",
  "project": {
    "name": "Marsden Valley Trapping Group",
    "about": {
      "summary": "Community trapping dashboard for the Marsden Valley Trapping Group, publishing public catch trends from Trap.NZ data.",
      "source_path": "docs/Trapping_Dashboard_Project_Summary_v2.docx"
    }
  },
  "source": {
    "project": "Marsden Valley Trapping Group",
    "published_from": "data/published/annual/all_project_data_*.csv"
  },
  "defaults": {
    "species": "Rat",
    "period": "last_6_months"
  },
  "periods": [
    {
      "key": "last_3_months",
      "label": "Last 3 months",
      "type": "rolling_months",
      "months": 3
    },
    {
      "key": "last_6_months",
      "label": "Last 6 months",
      "type": "rolling_months",
      "months": 6
    },
    {
      "key": "last_12_months",
      "label": "Last 12 months",
      "type": "rolling_months",
      "months": 12
    },
    {
      "key": "2019",
      "label": "2019",
      "type": "calendar_year",
      "year": 2019
    }
  ],
  "species": [
    "Rat",
    "Mouse",
    "Possum",
    "Mustelid",
    "All Species",
    "South Island Robin"
  ],
  "species_definitions": [
    {
      "key": "Rat",
      "label": "Rat",
      "measure_noun": "catches",
      "is_pest": true
    },
    {
      "key": "All Species",
      "label": "All Pest Species",
      "measure_noun": "catches",
      "is_pest": true
    },
    {
      "key": "South Island Robin",
      "label": "SI Robin",
      "measure_noun": "observations",
      "is_pest": false
    }
  ],
  "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
  "date_range": {
    "start": "2019-09-13",
    "end": "2026-08-08"
  },
  "notes": {
    "includes_bird_sightings": true,
    "includes_overwritten_rows": false,
    "includes_invalid_rows": false
  }
}
```

Notes:

- `project.name` is the preferred site-facing display name.
- `project.about` is available for a future project-information or about panel.
- `source.project` remains the published source label for compatibility with existing consumers.
- `species_definitions` lets the UI distinguish trap `catches` from bird `observations`.
- `species_definitions.label` lets the UI show shorter labels such as `SI Robin`.
- `species_definitions.is_pest` lets the UI distinguish pest and non-pest species in the selector.

## 2. weekly.json

Purpose:

- drives the main weekly series chart for a selected species and period
- also supports totals for the same filtered period

Format:

```json
{
  "schema_version": 1,
  "weeks": [
    {
      "week_start": "2026-01-05",
      "week_end": "2026-01-11",
      "year": 2026,
      "species": {
        "Rat": 3,
        "Mouse": 1,
        "Possum": 0,
        "Mustelid": 0,
        "All Species": 4
      }
    }
  ]
}
```

Notes:

- One row per week across the full dataset.
- `Mustelid` is the combined total of stoat, weasel, and ferret.
- `All Species` is the internal key for the selector label `All Pest Species`.
- `All Species` means all actual trap catches excluding `None` and `Unspecified`.
- bird observations are kept in separate species series and are not folded into `All Species`.
- The site filters the time window client-side using the ordered `metadata.periods` definitions, such as rolling 3, 6, or 12 month windows and single calendar years.

## 3. yearly_comparison.json

Purpose:

- supports the same-species all-years comparison chart
- allows comparison of seasonal shape by week number

Format:

```json
{
  "schema_version": 1,
  "series": {
    "Rat": {
      "2024": [0, 1, 0, 2],
      "2025": [1, 0, 3, 1],
      "2026": [0, 2, 1, 0]
    },
    "Mouse": {
      "2024": [0, 0, 1, 0]
    },
    "Possum": {
      "2024": [2, 1, 0, 3]
    },
    "Mustelid": {
      "2024": [0, 0, 0, 1]
    },
    "All Species": {
      "2024": [2, 2, 1, 6]
    }
  },
  "week_index": [1, 2, 3, 4]
}
```

Notes:

- Arrays are ordered by ISO week number.
- Missing weeks inside an observed year's range should be filled with `0`.
- Weeks outside an observed year's range may be `null` so incomplete years stop at the last available data point instead of implying zero catches.
- This file is intentionally chart-shaped rather than row-shaped.

## 4. summary.json

Purpose:

- supports totals cards and trend indicators
- avoids recalculating headline values in the browser

Format:

```json
{
  "schema_version": 1,
  "periods": {
    "last_3_months": {
      "species_totals": {
        "Rat": 12,
        "Mouse": 4,
        "Possum": 5,
        "Mustelid": 0,
        "All Species": 21
      },
      "trend": {
        "Rat": {
          "direction": "up",
          "delta": 3
        }
      }
    },
    "last_6_months": {
      "species_totals": {
        "Rat": 24,
        "Mouse": 12,
        "Possum": 8,
        "Mustelid": 1,
        "All Species": 45
      },
      "trend": {
        "Rat": {
          "direction": "up",
          "delta": 5
        },
        "All Species": {
          "direction": "down",
          "delta": -3
        }
      }
    },
    "2026": {
      "species_totals": {
        "Rat": 10,
        "Mouse": 7,
        "Possum": 4,
        "Mustelid": 1,
        "All Species": 22
      }
    }
  }
}
```

Notes:

- `last_3_months`, `last_6_months`, and `last_12_months` are rolling dashboard periods.
- `last_6_months` should be the default dashboard period.
- For each rolling period, trend should compare against the same seasonal window one year earlier.
- For annual periods from 2020 onward, trend should compare against the previous calendar year.
- For the latest incomplete year, the annual trend should compare year-to-date against the equivalent cutoff date in the prior year.
- `trend_context` may be included to support QA or debugging, but the dashboard does not need to render it permanently.

## Species Model

The site should expose these dashboard species groups:

- `Rat` = `Rat`, `Rat - Ship`, `Rat - Norway`, `Rat - Kiore`
- `Mouse` = `Mouse`
- `Possum` = `Possum`
- `Mustelid` = `Stoat`, `Weasel`, `Ferret`
- `All Species` = all actual pest catches excluding `None` and `Unspecified`, displayed in the UI as `All Pest Species`

Optional bird observation species can be appended to the species list when a private bird export is available.

Current first bird scope:

- `South Island Robin` = normalized bird-sightings sheet values such as `South Island Robin`, `Toutouwai`, or `Robin`, displayed in the UI as `SI Robin`
- bird observation species should use `observations` wording in UI summaries rather than `catches`
- bird observation species should be marked as non-pest in metadata so the selector can style them differently

## First Publish Scope

The first publish script should target only these outputs:

1. `metadata.json`
2. `weekly.json`
3. `yearly_comparison.json`
4. `summary.json`

That is enough to support the first proof-of-concept dashboard without committing yet to trap-line analytics or more detailed operational views.

## Current UI Notes

The current dashboard implementation uses:

- species radio-button navigation on the left
- a metadata-driven period control above the weekly chart, ordered as rolling windows first and then years from oldest to most recent
- summary metrics in a compact table
- year toggle buttons for the all-years comparison chart
- expand or close chart overlays for both charts

## Publish Input Strategy

The site publish step should read from the annual cleaned CSV files in `data/published/annual`.

Expected input pattern:

- `all_project_data_2019.csv`
- `all_project_data_2020.csv`
- `all_project_data_2026_to_2026-08-08.csv`

Why this is preferred:

- avoids treating one ever-growing `all_data.csv` file as the main working input
- supports future incremental rebuilds
- keeps year-scoped calculations natural for annual comparisons
- makes rolling-window calculations possible with only the needed year files

`all_data.csv` can remain as a convenience export for inspection, but it should not be the primary input to the publish layer.

Privacy note:

- The public annual CSV files are now privacy-filtered and intentionally contain only the publication whitelist used by downstream publishing.
- Detailed invalid review rows belong under `data/review/annual`, not under the published site data path.
