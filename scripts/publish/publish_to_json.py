import argparse
from collections import defaultdict
import csv
from datetime import date
from datetime import datetime
from glob import glob
import json
import logging
import os
import sys

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)
SCRIPTS_FOLDER = os.path.dirname(SCRIPT_FOLDER)
if SCRIPTS_FOLDER not in sys.path:
    sys.path.insert(0, SCRIPTS_FOLDER)

from transform.domain_constants import MUSTELID_SPECIES
from transform.domain_constants import RAT_SPECIES
from transform.domain_constants import SPECIES_COLLECTION_MUSTELID
from transform.domain_constants import SPECIES_COLLECTION_RAT
from transform.domain_constants import SPECIES_MOUSE
from transform.domain_constants import SPECIES_NONE
from transform.domain_constants import SPECIES_POSSUM
from transform.domain_constants import SPECIES_UNSPECIFIED
from script_logging import configure_script_logging


LOGGER = logging.getLogger()
SCHEMA_VERSION = 1
DATE_FMTS = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
SITE_SPECIES = [
    SPECIES_COLLECTION_RAT,
    SPECIES_MOUSE,
    SPECIES_POSSUM,
    SPECIES_COLLECTION_MUSTELID,
    "All Species",
]
ACTUAL_CATCH_EXCLUSIONS = {SPECIES_NONE, SPECIES_UNSPECIFIED}


def parse_record_date(value):
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError("could not parse record date {}".format(value))


def get_annual_files(path):
    if os.path.isfile(path):
        return [path]
    filenames = sorted(glob(os.path.join(path, "all_project_data_*.csv")))
    if not filenames:
        raise ValueError("no annual csv files found in {}".format(path))
    return filenames


def ensure_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
        LOGGER.info("created %s", folder)
    return folder


def get_site_species_counts(species, strikes):
    counts = {site_species: 0 for site_species in SITE_SPECIES}
    if species in RAT_SPECIES:
        counts[SPECIES_COLLECTION_RAT] = strikes
    if species == SPECIES_MOUSE:
        counts[SPECIES_MOUSE] = strikes
    if species == SPECIES_POSSUM:
        counts[SPECIES_POSSUM] = strikes
    if species in MUSTELID_SPECIES:
        counts[SPECIES_COLLECTION_MUSTELID] = strikes
    if species not in ACTUAL_CATCH_EXCLUSIONS:
        counts["All Species"] = strikes
    return counts


def add_species_counts(target, counts):
    for species_name, value in counts.items():
        target[species_name] += value


def blank_species_counts():
    return {species_name: 0 for species_name in SITE_SPECIES}


def shift_months(source_date, months):
    month_index = (source_date.year * 12 + source_date.month - 1) + months
    target_year = month_index // 12
    target_month = month_index % 12 + 1
    month_lengths = [31, 29 if target_year % 4 == 0 and (target_year % 100 != 0 or target_year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    target_day = min(source_date.day, month_lengths[target_month - 1])
    return date(target_year, target_month, target_day)


def get_period_totals(rows, start_date, end_date):
    totals = blank_species_counts()
    for row_date, species_counts in rows:
        if start_date <= row_date <= end_date:
            add_species_counts(totals, species_counts)
    return totals


def get_trend(current_totals, previous_totals):
    trend = {}
    for species_name in SITE_SPECIES:
        delta = current_totals[species_name] - previous_totals[species_name]
        direction = "flat"
        if delta > 0:
            direction = "up"
        elif delta < 0:
            direction = "down"
        trend[species_name] = {
            "direction": direction,
            "delta": delta,
        }
    return trend


def write_json(output_file, payload):
    with open(output_file, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
        fp.write("\n")


def load_publish_data(path):
    annual_files = get_annual_files(path)
    LOGGER.info("reading %d annual files", len(annual_files))

    weekly_counts = defaultdict(blank_species_counts)
    yearly_week_counts = {
        species_name: defaultdict(lambda: defaultdict(int)) for species_name in SITE_SPECIES
    }
    dated_rows = []
    years = set()
    year_week_ranges = defaultdict(lambda: {"min": None, "max": None})
    first_date = None
    last_date = None
    project_name = ""
    row_count = 0

    for filename in annual_files:
        LOGGER.info("reading %s", os.path.basename(filename))
        with open(filename, "r", newline="", encoding="utf-8-sig") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                row_count += 1
                if not project_name:
                    project_name = row.get("project", "")
                record_dt = parse_record_date(row["record_date"])
                record_day = record_dt.date()
                strikes = int(float(row.get("strikes") or 0))
                species = row.get("species_caught", SPECIES_NONE)
                species_counts = get_site_species_counts(species, strikes)
                dated_rows.append((record_day, species_counts))

                years.add(record_day.year)
                if first_date is None or record_day < first_date:
                    first_date = record_day
                if last_date is None or record_day > last_date:
                    last_date = record_day

                week_start = record_day.fromordinal(record_day.toordinal() - record_day.weekday())
                add_species_counts(weekly_counts[week_start], species_counts)

                week_index = record_day.isocalendar()[1]
                year_week_range = year_week_ranges[record_day.year]
                if year_week_range["min"] is None or week_index < year_week_range["min"]:
                    year_week_range["min"] = week_index
                if year_week_range["max"] is None or week_index > year_week_range["max"]:
                    year_week_range["max"] = week_index
                for species_name, value in species_counts.items():
                    yearly_week_counts[species_name][record_day.year][week_index] += value

    if row_count == 0:
        raise ValueError("no rows found in annual csv files")

    LOGGER.info("loaded %d rows spanning %s to %s", row_count, first_date, last_date)
    return {
        "annual_files": annual_files,
        "project_name": project_name,
        "weekly_counts": weekly_counts,
        "yearly_week_counts": yearly_week_counts,
        "dated_rows": dated_rows,
        "years": sorted(years),
        "year_week_ranges": dict(year_week_ranges),
        "first_date": first_date,
        "last_date": last_date,
    }


def build_metadata(publish_data):
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "source": {
            "project": publish_data["project_name"],
            "published_from": "data/published/annual/all_project_data_*.csv",
        },
        "defaults": {
            "species": SPECIES_COLLECTION_RAT,
            "period": "last_6_months",
        },
        "species": SITE_SPECIES,
        "years": publish_data["years"],
        "date_range": {
            "start": publish_data["first_date"].isoformat(),
            "end": publish_data["last_date"].isoformat(),
        },
        "notes": {
            "includes_overwritten_rows": False,
            "includes_invalid_rows": False,
        },
    }


def build_weekly_json(publish_data):
    weeks = []
    for week_start in sorted(publish_data["weekly_counts"]):
        week_end = week_start.fromordinal(week_start.toordinal() + 6)
        weeks.append(
            {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "year": week_start.year,
                "species": publish_data["weekly_counts"][week_start],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "weeks": weeks,
    }


def build_yearly_comparison_json(publish_data):
    max_week_index = 0
    for species_years in publish_data["yearly_week_counts"].values():
        for week_counts in species_years.values():
            if week_counts:
                max_week_index = max(max_week_index, max(week_counts.keys()))
    week_index = list(range(1, max_week_index + 1))
    latest_year = publish_data["last_date"].year

    series = {}
    for species_name in SITE_SPECIES:
        series[species_name] = {}
        for year in publish_data["years"]:
            week_counts = publish_data["yearly_week_counts"][species_name].get(year, {})
            week_range = publish_data["year_week_ranges"].get(year, {"min": None, "max": None})
            min_week = week_range["min"]
            max_week = week_range["max"]
            year_series = [
                week_counts.get(index, 0) if min_week is not None and min_week <= index <= max_week else None
                for index in week_index
            ]
            if year == latest_year and max_week is not None:
                year_series = trim_trailing_zero_weeks(year_series)
            series[species_name][str(year)] = year_series
    return {
        "schema_version": SCHEMA_VERSION,
        "series": series,
        "week_index": week_index,
    }


def trim_trailing_zero_weeks(year_series):
    result = list(year_series)
    trailing_index = len(result) - 1
    while trailing_index >= 0 and result[trailing_index] is None:
        trailing_index -= 1
    while trailing_index >= 0 and result[trailing_index] == 0:
        result[trailing_index] = None
        trailing_index -= 1
    return result


def build_summary_json(publish_data):
    max_date = publish_data["last_date"]
    current_start = shift_months(max_date, -6)
    previous_start = shift_months(current_start, -12)
    previous_end = shift_months(max_date, -12)
    latest_year = publish_data["last_date"].year

    periods = {}
    current_totals = get_period_totals(publish_data["dated_rows"], current_start, max_date)
    previous_totals = get_period_totals(publish_data["dated_rows"], previous_start, previous_end)
    periods["last_6_months"] = {
        "species_totals": current_totals,
        "trend": get_trend(current_totals, previous_totals),
        "trend_context": {
            "current_period": {
                "start": current_start.isoformat(),
                "end": max_date.isoformat(),
                "species_totals": current_totals,
            },
            "previous_period": {
                "start": previous_start.isoformat(),
                "end": previous_end.isoformat(),
                "species_totals": previous_totals,
            },
        },
    }

    for year in publish_data["years"]:
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        year_totals = get_period_totals(publish_data["dated_rows"], year_start, year_end)
        periods[str(year)] = {
            "species_totals": year_totals,
        }
        previous_year = year - 1
        if previous_year in publish_data["years"]:
            previous_year_start = date(previous_year, 1, 1)
            if year == latest_year:
                previous_year_end = shift_months(publish_data["last_date"], -12)
                current_year_end = publish_data["last_date"]
            else:
                previous_year_end = date(previous_year, 12, 31)
                current_year_end = year_end
            previous_year_totals = get_period_totals(
                publish_data["dated_rows"], previous_year_start, previous_year_end
            )
            current_year_totals = get_period_totals(
                publish_data["dated_rows"], year_start, current_year_end
            )
            periods[str(year)]["species_totals"] = current_year_totals
            periods[str(year)]["trend"] = get_trend(current_year_totals, previous_year_totals)
            periods[str(year)]["trend_context"] = {
                "current_period": {
                    "start": year_start.isoformat(),
                    "end": current_year_end.isoformat(),
                    "species_totals": current_year_totals,
                },
                "previous_period": {
                    "start": previous_year_start.isoformat(),
                    "end": previous_year_end.isoformat(),
                    "species_totals": previous_year_totals,
                },
            }

    return {
        "schema_version": SCHEMA_VERSION,
        "periods": periods,
    }


def get_cmd_args(title):
    parser = argparse.ArgumentParser(title)
    parser.add_argument(
        "-p",
        "--path",
        help="path to cleaned annual csv files",
        default="../../data/published/annual",
    )
    parser.add_argument(
        "-of",
        "--output_folder",
        help="folder to save published json files to",
        default="../../site/data",
    )
    return parser.parse_args()


def get_basename_only(path=__file__):
    base_filename_only, _ext = os.path.splitext(os.path.basename(path))
    return base_filename_only


def main():
    base_folder = SCRIPT_FOLDER
    base_filename_only = get_basename_only()
    initial_wd = os.getcwd()
    if initial_wd != base_folder:
        os.chdir(base_folder)
    try:
        args = get_cmd_args(base_filename_only)
        configure_script_logging(LOGGER, SCRIPT_PATH)
        LOGGER.info("args: %s", args)
        LOGGER.info("cwd: %s", os.getcwd())

        publish_data = load_publish_data(args.path)
        output_folder = ensure_folder(args.output_folder)

        metadata = build_metadata(publish_data)
        weekly = build_weekly_json(publish_data)
        yearly_comparison = build_yearly_comparison_json(publish_data)
        summary = build_summary_json(publish_data)

        write_json(os.path.join(output_folder, "metadata.json"), metadata)
        write_json(os.path.join(output_folder, "weekly.json"), weekly)
        write_json(os.path.join(output_folder, "yearly_comparison.json"), yearly_comparison)
        write_json(os.path.join(output_folder, "summary.json"), summary)
        LOGGER.info("saved published json files to %s", output_folder)
    finally:
        if initial_wd != base_folder:
            os.chdir(initial_wd)


if __name__ == "__main__":
    main()