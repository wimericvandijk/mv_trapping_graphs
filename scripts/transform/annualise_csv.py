import argparse

from collections import defaultdict
from datetime import datetime
import csv
import fnmatch
from glob import glob
import json
import logging
import os
import re
import sys

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)
SCRIPTS_FOLDER = os.path.dirname(SCRIPT_FOLDER)
if SCRIPTS_FOLDER not in sys.path:
    sys.path.insert(0, SCRIPTS_FOLDER)

from script_logging import configure_script_logging

from domain_constants import ALL_SPECIES
from domain_constants import SPECIES_BIRD
from domain_constants import SPECIES_CAT
from domain_constants import SPECIES_FERRET
from domain_constants import SPECIES_HEDGEHOG
from domain_constants import SPECIES_MAGPIE
from domain_constants import SPECIES_MOUSE
from domain_constants import SPECIES_NONE
from domain_constants import SPECIES_OTHER
from domain_constants import SPECIES_POSSUM
from domain_constants import SPECIES_RABBIT
from domain_constants import SPECIES_RAT
from domain_constants import SPECIES_RAT_KIORE
from domain_constants import SPECIES_RAT_NORWAY
from domain_constants import SPECIES_RAT_SHIP
from domain_constants import SPECIES_STOAT
from domain_constants import SPECIES_UNSPECIFIED
from domain_constants import SPECIES_WEASEL
from domain_constants import SPECIES_WEKA
from domain_constants import TRAP_TYPE_A12
from domain_constants import TRAP_TYPE_A24
from domain_constants import TRAP_TYPE_AT220
from domain_constants import TRAP_TYPE_BT_200
from domain_constants import TRAP_TYPE_D_RAT
from domain_constants import TRAP_TYPE_DOC_150
from domain_constants import TRAP_TYPE_DOC_200
from domain_constants import TRAP_TYPE_POSSUM_MASTER
from domain_constants import TRAP_TYPE_RAT_TRAP
from domain_constants import TRAP_TYPE_SA_CAT
from domain_constants import TRAP_TYPE_SENTINEL
from domain_constants import TRAP_TYPE_TIMMS
from domain_constants import TRAP_TYPE_T_REX_RAT_TRAP
from domain_constants import TRAP_TYPE_TRAPINATOR
from domain_constants import TRAP_TYPE_VICTOR

LOGGER = logging.getLogger()
DATESTAMP_FMT = "%Y%m%d"
CSV_TIMESTAMP_FMTS = [
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
]

TRAP_CODE_COL = "trap_code"
LINE_COL = "line"
DATE_COL = "record_date"
TRAP_ID_COL = "trap_id"
SPECIES_COL = "species_caught"
TRAP_TYPE_COL = "trap_type"
TRAP_SUB_TYPE_COL = "trap_sub_type"
RULE_BROKEN_COL = "rule_broken"
DEFAULT_RULES_CONFIG = "../../config/trap_species_rules.json"
DEFAULT_REVIEW_OUTPUT_FOLDER = "../../data/review/annual"
RECENT_RECORD_GLOB = "*trap-records-recent*.csv"

REQUIRED_RECORD_COLS = [TRAP_ID_COL, TRAP_CODE_COL, DATE_COL]
REQUIRED_TRAP_COLS = [TRAP_ID_COL, "code", TRAP_TYPE_COL]
PRIVATE_COLS = ['recorded_by', 'username']
PUBLIC_RECORD_FIELDNAMES = [
    "project",
    DATE_COL,
    TRAP_ID_COL,
    TRAP_CODE_COL,
    LINE_COL,
    TRAP_TYPE_COL,
    "strikes",
    SPECIES_COL,
    "clean_datestamp",
    "clean_rule_status",
    RULE_BROKEN_COL,
    "clean_rule_reason",
]

SPECIES_SYNONYMS = {
    "": SPECIES_NONE,
    "none": SPECIES_NONE,
    "unspecified": SPECIES_UNSPECIFIED,
    "rat": SPECIES_RAT,
    "rat - ship": SPECIES_RAT_SHIP,
    "rat-ship": SPECIES_RAT_SHIP,
    "ship rat": SPECIES_RAT_SHIP,
    "rat - norway": SPECIES_RAT_NORWAY,
    "norway rat": SPECIES_RAT_NORWAY,
    "rat - kiore": SPECIES_RAT_KIORE,
    "kiore": SPECIES_RAT_KIORE,
    "mouse": SPECIES_MOUSE,
    "possum": SPECIES_POSSUM,
    "stoat": SPECIES_STOAT,
    "weasel": SPECIES_WEASEL,
    "ferret": SPECIES_FERRET,
    "hedgehog": SPECIES_HEDGEHOG,
    "bird": SPECIES_BIRD,
    "cat": SPECIES_CAT,
    "weka": SPECIES_WEKA,
    "magpie": SPECIES_MAGPIE,
    "rabbit": SPECIES_RABBIT,
    "other": SPECIES_OTHER,
}

TRAP_TYPE_SYNONYMS = {
    "doc200": TRAP_TYPE_DOC_200,
    "doc 200": TRAP_TYPE_DOC_200,
    "doc150": TRAP_TYPE_DOC_150,
    "doc 150": TRAP_TYPE_DOC_150,
    "a24": TRAP_TYPE_A24,
    "a12": TRAP_TYPE_A12,
    "at220": TRAP_TYPE_AT220,
    "victor": TRAP_TYPE_VICTOR,
    "trapinator": TRAP_TYPE_TRAPINATOR,
    "possum master": TRAP_TYPE_POSSUM_MASTER,
    "t-rex rat trap": TRAP_TYPE_T_REX_RAT_TRAP,
    "t rex rat trap": TRAP_TYPE_T_REX_RAT_TRAP,
    "d-rat": TRAP_TYPE_D_RAT,
    "drat": TRAP_TYPE_D_RAT,
    "timms": TRAP_TYPE_TIMMS,
    "sa cat": TRAP_TYPE_SA_CAT,
    "sentinel": TRAP_TYPE_SENTINEL,
    "bt 200": TRAP_TYPE_BT_200,
    "rat trap": TRAP_TYPE_RAT_TRAP,
}

ALLOW_NO_CATCH_ONLY = {SPECIES_NONE, SPECIES_UNSPECIFIED}
TRAP_RULES = {
    "species_collections": {},
    "restricted_species": set(),
    "trap_type_allowed_species": {},
}


def get_year_from_datestamp(datestamp, as_int=False):
    result = datestamp[:4]
    if as_int:
        return int(result)
    return result

def get_latest_timestamp_in(year_data):
    if not year_data:
        return '', None
    result = ''
    latest = None
    for row in year_data:
        cell = row[DATE_COL]
        try:
            dt = parse_timestamp(cell)
        except ValueError:
            continue
        if latest is None or dt > latest:
            result = cell
            latest = dt
    return result, latest


def get_public_fieldnames(fieldnames):
    return [fieldname for fieldname in PUBLIC_RECORD_FIELDNAMES if fieldname in fieldnames]


def project_public_rows(rows, fieldnames):
    return [
        {fieldname: row.get(fieldname, "") for fieldname in fieldnames}
        for row in rows
    ]


def build_year_data(csv_data):
    year_data = defaultdict(list)
    for datestamp in sorted(csv_data):
        lines = csv_data[datestamp]
        year_data[get_year_from_datestamp(datestamp)].extend(lines)
    return year_data


def get_output_fieldnames(fieldnames, public_only):
    if public_only:
        return get_public_fieldnames(fieldnames)
    return list(fieldnames)


def get_annual_output_filename(output_folder, year, latest_dt):
    output_file_base = "{}/all_project_data_{}".format(output_folder, year)
    days_to_eoy = (datetime(int(year), 12, 31) - latest_dt).total_seconds() / 60 / 60 / 24
    if days_to_eoy > 10:
        output_file_base += '_to_{}'.format(latest_dt.strftime("%Y-%m-%d"))
    return output_file_base + '.csv'


def remove_existing_year_files(output_folder, year):
    pattern = os.path.join(output_folder, "all_project_data_{}*.csv".format(year))
    for existing_file in glob(pattern):
        os.remove(existing_file)
        LOGGER.info("removed stale %s", existing_file)


def get_saved_annual_files(output_folder):
    return sorted(glob(os.path.join(output_folder, "all_project_data_*.csv")))


def get_annual_file_year(filename):
    match = re.search(r"all_project_data_(\d{4})", os.path.basename(filename))
    if not match:
        return None
    return match.group(1)


def rebuild_combined_output_file(output_folder, fieldnames, public_only):
    annual_files = get_saved_annual_files(output_folder)
    all_rows = []
    output_fieldnames = get_output_fieldnames(fieldnames, public_only)
    for annual_file in annual_files:
        with open(annual_file, "r", newline="", encoding="utf-8-sig") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                all_rows.append(row)
    all_output_file = os.path.join(output_folder, "all_data.csv")
    write_rows(all_output_file, output_fieldnames, all_rows)
    LOGGER.info("saved %d lines to %s", len(all_rows) + 1, all_output_file)
    return all_output_file


def save_annual_csv(fieldnames, csv_data, output_folder, public_only=True, years_to_write=None):
    """
    Writes annualised csv files into output_folder.
        Any existing files in that folder with the same names will be overwritten
    Args:
        csv_header:
        csv_data:
        output_folder:

    Returns: [str]  list of output filenames

    """
    result = []
    output_fieldnames = get_output_fieldnames(fieldnames, public_only)
    year_data = build_year_data(csv_data)
    if years_to_write is None:
        years_to_write = sorted(year_data)
    else:
        years_to_write = sorted({str(year) for year in years_to_write})

    for year in years_to_write:
        remove_existing_year_files(output_folder, year)
        output_rows = year_data.get(year, [])
        if not output_rows:
            continue
        latest_timestamp, latest_dt = get_latest_timestamp_in(output_rows)
        if not latest_timestamp:
            continue
        output_file = get_annual_output_filename(output_folder, year, latest_dt)
        rows_to_write = output_rows
        if public_only:
            rows_to_write = project_public_rows(output_rows, output_fieldnames)
        write_rows(output_file, output_fieldnames, rows_to_write)
        LOGGER.info("saved %d lines to %s, latest timestamp= %s", len(output_rows) + 1, output_file,
                    latest_timestamp)
        result.append(output_file)
    result.append(rebuild_combined_output_file(output_folder, fieldnames, public_only))
    return result


def parse_timestamp(row_value):
    for fmt in CSV_TIMESTAMP_FMTS:
        try:
            return datetime.strptime(row_value, fmt)
        except ValueError:
            continue
    raise ValueError('could not parse timestamp "{}"'.format(row_value))


def get_datestamp(row_value):
    dt = parse_timestamp(row_value)
    return dt.strftime(DATESTAMP_FMT)


def normalise_trap_type(trap_type):
    value = (trap_type or "").strip()
    if not value:
        return ""
    return TRAP_TYPE_SYNONYMS.get(value.lower(), value)


def normalise_species(species):
    value = (species or "").strip()
    return SPECIES_SYNONYMS.get(value.lower(), value or "None")


def sanitise_project_name(project_name):
    value = (project_name or "").strip()
    if not value:
        return ""
    return value.split(",", 1)[0].strip()


def expand_species_entries(entries, species_collections):
    expanded_species = set()
    for entry in entries:
        normalised_entry = normalise_species(entry)
        collection_species = species_collections.get(normalised_entry)
        if collection_species:
            expanded_species.update(collection_species)
        else:
            expanded_species.add(normalised_entry)
    return expanded_species


def load_trap_rules(config_path):
    with open(config_path, "r", encoding="utf-8") as fp:
        raw_rules = json.load(fp)
    species_collections = {}
    for collection_name, collection_species in raw_rules.get("species_collections", {}).items():
        normalised_collection_name = normalise_species(collection_name)
        species_collections[normalised_collection_name] = {
            normalise_species(species)
            for species in collection_species
        }
    restricted_species = expand_species_entries(
        raw_rules.get("restricted_species", []),
        species_collections,
    )
    trap_type_allowed_species = {}
    for trap_type, allowed_species in raw_rules.get("trap_type_allowed_species", {}).items():
        normalised_trap_type = normalise_trap_type(trap_type)
        trap_type_allowed_species[normalised_trap_type] = expand_species_entries(
            allowed_species,
            species_collections,
        )
    return {
        "species_collections": species_collections,
        "restricted_species": restricted_species,
        "trap_type_allowed_species": trap_type_allowed_species,
    }


def get_allowed_species(trap_type):
    return TRAP_RULES["trap_type_allowed_species"].get(trap_type, ALLOW_NO_CATCH_ONLY)


def get_trap_day_key(row):
    return "{}|{}".format(row[TRAP_ID_COL], get_datestamp(row[DATE_COL]))


def get_raw_files(path, record_glob="*trap-records*.csv"):
    if os.path.isfile(path):
        folder = os.path.dirname(path) or "."
    else:
        folder = path
    record_files = sorted(glob(os.path.join(folder, record_glob)))
    if record_glob == "*trap-records*.csv":
        record_files = [
            filename for filename in record_files
            if not fnmatch.fnmatch(os.path.basename(filename), RECENT_RECORD_GLOB)
        ]
    trap_files = sorted(glob(os.path.join(folder, "*traps*.csv")))
    trap_files = [filename for filename in trap_files if "trap-records" not in os.path.basename(filename)]
    if not record_files:
        raise ValueError("no trap record csv files found in {}".format(folder))
    if not trap_files:
        raise ValueError("no trap metadata csv files found in {}".format(folder))
    return record_files, trap_files


def load_trap_lookup(trap_files):
    trap_lookup = {}
    for filename in trap_files:
        basename_only = get_basename_only(filename)
        LOGGER.info("reading trap metadata %s", basename_only)
        with open(filename, "r", newline="", encoding="utf-8-sig") as fp:
            reader = csv.DictReader(fp)
            missing_cols = [col for col in REQUIRED_TRAP_COLS if col not in reader.fieldnames]
            if missing_cols:
                raise ValueError("{} missing trap columns {}".format(basename_only, missing_cols))
            
            for row in reader:
                trap_id = (row.get(TRAP_ID_COL) or "").strip()
                if not trap_id:
                    continue
                row[TRAP_TYPE_COL] = normalise_trap_type(row.get(TRAP_TYPE_COL))
                for private_col in PRIVATE_COLS:
                    row[private_col] = ""
                trap_lookup[trap_id] = row
    return trap_lookup


def cleanse_record(row, trap_lookup):
    cleaned = dict(row)
    for private_col in PRIVATE_COLS:
        cleaned[private_col] = ""
    if "project" in cleaned:
        cleaned["project"] = sanitise_project_name(cleaned.get("project"))
    cleaned[SPECIES_COL] = normalise_species(cleaned.get(SPECIES_COL))
    trap_id = (cleaned.get(TRAP_ID_COL) or "").strip()
    trap_meta = trap_lookup.get(trap_id)
    if trap_meta:
        cleaned["trap_code_source"] = "metadata"
        cleaned["trap_type_source"] = "metadata"
        cleaned[TRAP_CODE_COL] = trap_meta.get("code") or cleaned.get(TRAP_CODE_COL, "")
        cleaned[TRAP_TYPE_COL] = trap_meta.get(TRAP_TYPE_COL, "")
        cleaned[TRAP_SUB_TYPE_COL] = trap_meta.get(TRAP_SUB_TYPE_COL, "")
        cleaned[LINE_COL] = cleaned.get(LINE_COL) or trap_meta.get(LINE_COL, "")
    else:
        cleaned["trap_code_source"] = "records"
        cleaned["trap_type_source"] = "records"
        cleaned[TRAP_TYPE_COL] = normalise_trap_type(cleaned.get(TRAP_TYPE_COL))
        cleaned[TRAP_SUB_TYPE_COL] = cleaned.get(TRAP_SUB_TYPE_COL, "")
    cleaned["clean_datestamp"] = get_datestamp(cleaned[DATE_COL])
    cleaned["clean_rule_status"] = "valid"
    cleaned[RULE_BROKEN_COL] = ""
    cleaned["clean_rule_reason"] = ""
    return cleaned


def is_record_allowed(row):
    trap_type = row.get(TRAP_TYPE_COL, "")
    species = row.get(SPECIES_COL, "None")
    if species not in TRAP_RULES["restricted_species"]:
        return True, ""
    allowed_species = get_allowed_species(trap_type)
    if species not in allowed_species:
        return False, "{} in {}?".format(species, trap_type or "<missing>")
    return True, ""


def mark_rejected_row(row, rule_broken, reason):
    rejected = dict(row)
    rejected["clean_rule_status"] = "invalid"
    rejected[RULE_BROKEN_COL] = rule_broken
    rejected["clean_rule_reason"] = reason
    return rejected


def get_csv_data(path, record_glob="*trap-records*.csv"):
    """
    reads in all CSV data, ignoring duplicate lines

    Args:
        path: folder containing csv data

    Returns: (csv_header, csv_data)
    fieldnames are the output columns written to the cleaned annual files.
    csv_data: {datestamp: [row-as-dict]}  datestamp is in DATESTAMP_FMT

    """

    csv_data = defaultdict(list)
    unique_key_data = {}
    invalid_rows = []
    record_files, trap_files = get_raw_files(path, record_glob=record_glob)
    trap_lookup = load_trap_lookup(trap_files)
    fieldnames = None
    for filename in record_files:
        basename_only = get_basename_only(filename)
        LOGGER.info("reading %s", basename_only)
        with open(filename, "r", newline="", encoding="utf-8-sig") as fp:
            reader = csv.DictReader(fp)
            if not reader.fieldnames:
                LOGGER.info("empty file - ignoring")
                continue
            missing_cols = [col for col in REQUIRED_RECORD_COLS if col not in reader.fieldnames]
            if missing_cols:
                LOGGER.warning(
                    "%s missing record columns %s - skipping incompatible file",
                    basename_only,
                    missing_cols,
                )
                continue
            for row in reader:
                if not (row.get(TRAP_ID_COL) and row.get(DATE_COL)):
                    continue
                cleaned = cleanse_record(row, trap_lookup)
                is_allowed, reason = is_record_allowed(cleaned)
                if not is_allowed:
                    invalid_rows.append(mark_rejected_row(cleaned, "wrong trap type", reason))
                    continue
                datestamp = cleaned["clean_datestamp"]
                unique_key = get_trap_day_key(cleaned)
                if fieldnames is None:
                    fieldnames = list(cleaned.keys())
                if unique_key in unique_key_data:
                    existing_datestamp, line_index = unique_key_data[unique_key]
                    overwritten_row = csv_data[existing_datestamp][line_index]
                    LOGGER.debug(
                        "overwriting previous data for %s from %s with later row",
                        unique_key,
                        basename_only,
                    )
                    invalid_rows.append(
                        mark_rejected_row(
                            overwritten_row,
                            "overwritten",
                            "by {}".format(cleaned[DATE_COL]),
                        )
                    )
                    csv_data[existing_datestamp][line_index] = cleaned
                    if existing_datestamp != datestamp:
                        csv_data[datestamp].append(csv_data[existing_datestamp].pop(line_index))
                        unique_key_data[unique_key] = (datestamp, len(csv_data[datestamp]) - 1)
                else:
                    unique_key_data[unique_key] = (datestamp, len(csv_data[datestamp]))
                    csv_data[datestamp].append(cleaned)

    if fieldnames is None:
        raise ValueError("no valid trap record rows found")
    return fieldnames, csv_data, invalid_rows


def write_rows(output_file, fieldnames, rows):
    with open(output_file, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def save_invalid_rows(invalid_rows, output_folder):
    if not invalid_rows:
        LOGGER.info("no invalid trap/species rows found")
        return None
    output_file = os.path.join(output_folder, "invalid_records.csv")
    public_fieldnames = get_public_fieldnames(invalid_rows[0].keys())
    write_rows(output_file, public_fieldnames, project_public_rows(invalid_rows, public_fieldnames))
    LOGGER.info("saved %d invalid rows to %s", len(invalid_rows), output_file)
    return output_file


def save_review_rows(invalid_rows, output_folder):
    if not invalid_rows:
        return None
    review_folder = __ensure_folder(output_folder)
    output_file = os.path.join(review_folder, "invalid_records.csv")
    write_rows(output_file, list(invalid_rows[0].keys()), invalid_rows)
    LOGGER.info("saved %d detailed invalid rows to %s", len(invalid_rows), output_file)
    return output_file


def load_existing_annual_csv_data(output_folder, years=None):
    csv_data = defaultdict(list)
    fieldnames = None
    requested_years = None if years is None else {str(year) for year in years}
    for filename in get_saved_annual_files(output_folder):
        file_year = get_annual_file_year(filename)
        if requested_years is not None and file_year not in requested_years:
            continue
        with open(filename, "r", newline="", encoding="utf-8-sig") as fp:
            reader = csv.DictReader(fp)
            if not reader.fieldnames:
                continue
            if fieldnames is None:
                fieldnames = list(reader.fieldnames)
            for row in reader:
                datestamp = row.get("clean_datestamp") or get_datestamp(row[DATE_COL])
                csv_data[datestamp].append(row)
    return fieldnames, csv_data


def load_existing_invalid_rows(output_folder):
    output_file = os.path.join(output_folder, "invalid_records.csv")
    if not os.path.exists(output_file):
        return []
    with open(output_file, "r", newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        return list(reader)


def get_earliest_timestamp_in(csv_data):
    earliest = None
    for rows in csv_data.values():
        for row in rows:
            try:
                dt = parse_timestamp(row[DATE_COL])
            except ValueError:
                continue
            if earliest is None or dt < earliest:
                earliest = dt
    return earliest


def get_years_in_csv_data(csv_data):
    return sorted({get_year_from_datestamp(datestamp) for datestamp in csv_data})


def is_row_before_cutoff(row, cutoff_dt):
    return parse_timestamp(row[DATE_COL]) < cutoff_dt


def merge_csv_data(existing_csv_data, recent_csv_data, cutoff_dt):
    merged_csv_data = defaultdict(list)
    for datestamp, rows in existing_csv_data.items():
        preserved_rows = [row for row in rows if is_row_before_cutoff(row, cutoff_dt)]
        if preserved_rows:
            merged_csv_data[datestamp].extend(preserved_rows)
    for datestamp, rows in recent_csv_data.items():
        merged_csv_data[datestamp].extend(rows)
    return merged_csv_data


def merge_invalid_rows(existing_invalid_rows, recent_invalid_rows, cutoff_dt):
    merged_rows = []
    for row in existing_invalid_rows:
        if is_row_before_cutoff(row, cutoff_dt):
            merged_rows.append(row)
    merged_rows.extend(recent_invalid_rows)
    return merged_rows


def merge_recent_transform(args):
    review_output_folder = __ensure_folder(args.review_output_folder)
    public_output_folder = __ensure_folder(args.output_folder)
    recent_fieldnames, recent_csv_data, recent_invalid_rows = get_csv_data(
        args.path,
        record_glob=RECENT_RECORD_GLOB,
    )
    cutoff_dt = get_earliest_timestamp_in(recent_csv_data)
    if cutoff_dt is None:
        raise ValueError("no recent trap record rows found for merge")
    impacted_years = get_years_in_csv_data(recent_csv_data)
    detailed_fieldnames, existing_csv_data = load_existing_annual_csv_data(
        review_output_folder,
        years=impacted_years,
    )
    if detailed_fieldnames is None:
        raise ValueError(
            "no detailed annual files found in {}. Run the full annualise transform first.".format(
                review_output_folder
            )
        )
    merged_csv_data = merge_csv_data(existing_csv_data, recent_csv_data, cutoff_dt)
    existing_invalid_rows = load_existing_invalid_rows(review_output_folder)
    merged_invalid_review_rows = merge_invalid_rows(existing_invalid_rows, recent_invalid_rows, cutoff_dt)

    save_annual_csv(detailed_fieldnames or recent_fieldnames, merged_csv_data, review_output_folder, public_only=False, years_to_write=impacted_years)
    all_detailed_fieldnames, all_review_csv_data = load_existing_annual_csv_data(review_output_folder)
    save_annual_csv(
        all_detailed_fieldnames or detailed_fieldnames or recent_fieldnames,
        all_review_csv_data,
        public_output_folder,
        public_only=True,
    )
    save_review_rows(merged_invalid_review_rows, review_output_folder)
    save_invalid_rows(merged_invalid_review_rows, public_output_folder)


def __ensure_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
        LOGGER.info("created %s", folder)
    return folder


def get_cmd_args(title):
    """

    Returns: argParse object

    """
    parser = argparse.ArgumentParser(title)

    parser.add_argument(
        "-p",
        "--path",
        help="path to raw Trap.NZ csv data - file or folder containing trap-records and traps exports",
        default="../../data/raw",
    )
    parser.add_argument(
        "-of",
        "--output_folder",
        help="folder to save cleaned annual output to",
        default="../../data/published/annual",
    )
    parser.add_argument(
        "-rc",
        "--rules_config",
        help="json file containing trap/species policy rules",
        default=DEFAULT_RULES_CONFIG,
    )
    parser.add_argument(
        "-rof",
        "--review_output_folder",
        help="folder to save detailed internal annual and review csv outputs to",
        default=DEFAULT_REVIEW_OUTPUT_FOLDER,
    )
    parser.add_argument(
        "--merge_recent",
        action="store_true",
        help="merge the recent raw import into existing detailed annual files instead of rebuilding from all raw records",
    )
    return parser.parse_args()


def get_basename_only(path=__file__):
    base_filename_only, _ext = os.path.splitext(os.path.basename(path))
    return base_filename_only


def main():
    """main program"""
    global TRAP_RULES
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

        TRAP_RULES = load_trap_rules(args.rules_config)
        LOGGER.info("loaded trap rules from %s", args.rules_config)

        if args.merge_recent:
            merge_recent_transform(args)
        else:
            output_folder = __ensure_folder(args.output_folder)
            review_output_folder = __ensure_folder(args.review_output_folder)
            fieldnames, csv_data, invalid_rows = get_csv_data(args.path)
            save_annual_csv(fieldnames, csv_data, output_folder, public_only=True)
            save_annual_csv(fieldnames, csv_data, review_output_folder, public_only=False)
            save_invalid_rows(invalid_rows, output_folder)
            save_review_rows(invalid_rows, review_output_folder)
    finally:
        if initial_wd != base_folder:
            os.chdir(initial_wd)


if __name__ == "__main__":
    main()
