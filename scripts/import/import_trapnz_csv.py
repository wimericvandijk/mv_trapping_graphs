import argparse
from datetime import date
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)
SCRIPTS_FOLDER = os.path.dirname(SCRIPT_FOLDER)
if SCRIPTS_FOLDER not in sys.path:
    sys.path.insert(0, SCRIPTS_FOLDER)

from script_logging import configure_script_logging

LOGGER = logging.getLogger()
DEFAULT_SECRETS_PATH = "../../config/secrets.json"
DEFAULT_OUTPUT_FOLDER = "../../data/raw"
BASE_WFS_URL = "https://io.trap.nz/geo/trapnz-projects/wfs/{api_key}/{project_id}"
TRANSFORM_SCRIPT = "../transform/annualise_csv.py"
PUBLISH_SCRIPT = "../publish/publish_to_json.py"
DEFAULT_QUERY_NAMES = ["trap_list", "recent_records"]
DEFAULT_QUERY_SPECS = {
    "trap_list": {
        "type_name": "trapnz-projects:my-projects-traps",
        "output_file": "my-projects-traps.csv",
    },
    "recent_records": {
        "type_name": "trapnz-projects:my-projects-trap-records",
        "output_file": "my-projects-trap-records-recent.csv",
    },
    "all_records": {
        "type_name": "trapnz-projects:my-projects-trap-records",
        "output_file": "my-projects-trap-records.csv",
    },
}
ENV_API_KEY = "TRAPNZ_API_KEY"
ENV_PROJECT_ID = "TRAPNZ_PROJECT_ID"
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
}


def get_cmd_args(title):
    parser = argparse.ArgumentParser(title)
    parser.add_argument(
        "-sp",
        "--secrets_path",
        help="path to the ignored local Trap.NZ secrets file",
        default=DEFAULT_SECRETS_PATH,
    )
    parser.add_argument(
        "-of",
        "--output_folder",
        help="folder to save imported CSV files to",
        default=DEFAULT_OUTPUT_FOLDER,
    )
    parser.add_argument(
        "-q",
        "--query",
        action="append",
        dest="query_names",
        help="optional query name to run; may be provided multiple times",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="log the downloads that would run without making network requests",
    )
    parser.add_argument(
        "--no-import",
        action="store_true",
        help="skip Trap.NZ API calls but still allow follow-up merge or publish steps",
    )
    parser.add_argument(
        "--list-queries",
        action="store_true",
        help="list the available query names and exit",
    )
    parser.add_argument(
        "--merge-recent",
        action="store_true",
        help="run annualise_csv.py --merge_recent after importing recent raw files",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="run publish_to_json.py after import or recent-merge processing",
    )
    return parser.parse_args()


def get_basename_only(path=__file__):
    base_filename_only, _ext = os.path.splitext(os.path.basename(path))
    return base_filename_only


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def get_recent_records_start_date(today=None):
    today = today or date.today()
    first_day_of_current_month = today.replace(day=1)
    if first_day_of_current_month.month == 1:
        return first_day_of_current_month.replace(year=first_day_of_current_month.year - 1, month=12)
    return first_day_of_current_month.replace(month=first_day_of_current_month.month - 1)


def build_recent_records_cql_filter(today=None):
    start_date = get_recent_records_start_date(today)
    return "record_date>='{}'".format(start_date.isoformat())


def get_secret_value(env_name, config, *config_keys):
    env_value = os.getenv(env_name)
    if env_value not in {None, ""}:
        return env_value
    for key in config_keys:
        value = config.get(key)
        if value not in {None, ""}:
            return value
    return None


def get_query_specs(config):
    raw_queries = config.get("queries") or {}
    query_specs = {name: dict(spec) for name, spec in DEFAULT_QUERY_SPECS.items()}
    for query_name, raw_value in raw_queries.items():
        if isinstance(raw_value, str):
            query_specs[query_name] = {
                "url": raw_value,
                "output_file": DEFAULT_QUERY_SPECS.get(query_name, {}).get(
                    "output_file", f"{query_name}.csv"
                ),
            }
            continue
        query_specs[query_name] = {
            "type_name": raw_value.get("type_name", ""),
            "output_file": raw_value.get("output_file") or f"{query_name}.csv",
            "cql_filter": raw_value.get("cql_filter", ""),
        }
    return query_specs


def resolve_query_spec(query_name, query_spec):
    resolved = dict(query_spec)
    if query_name == "recent_records" and not resolved.get("url") and not resolved.get("cql_filter"):
        resolved["cql_filter"] = build_recent_records_cql_filter()
    return resolved


def get_default_query_names(query_specs):
    return [name for name in DEFAULT_QUERY_NAMES if name in query_specs]


def build_query_url(query_spec, api_key, project_id):
    if query_spec.get("url"):
        return query_spec["url"]
    if not api_key or not project_id:
        raise ValueError(
            "Trap.NZ credentials are required. Set TRAPNZ_API_KEY and TRAPNZ_PROJECT_ID or provide them in the ignored secrets file."
        )
    type_name = query_spec.get("type_name")
    if not type_name:
        raise ValueError("query is missing type_name")
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": "CSV",
    }
    cql_filter = query_spec.get("cql_filter")
    if cql_filter:
        params["cql_filter"] = cql_filter
    return BASE_WFS_URL.format(api_key=api_key, project_id=project_id) + "?" + urlencode(params)


def mask_logged_url(url, api_key, project_id):
    masked_url = url
    if api_key:
        masked_url = masked_url.replace(str(api_key), "<API_KEY>")
    if project_id:
        masked_url = masked_url.replace(str(project_id), "<project_id>")
    return masked_url


def ensure_folder(folder):
    os.makedirs(folder, exist_ok=True)
    return folder


def download_csv(url, output_file):
    request = Request(url, headers=DEFAULT_REQUEST_HEADERS)
    with urlopen(request) as response:
        payload = response.read()
    with open(output_file, "wb") as fp:
        fp.write(payload)


def run_imports(output_folder, query_specs, api_key, project_id, dry_run=False):
    output_folder = ensure_folder(output_folder)
    downloaded_files = []
    for query_name in sorted(query_specs):
        query_spec = resolve_query_spec(query_name, query_specs[query_name])
        output_file = os.path.join(output_folder, query_spec["output_file"])
        url = build_query_url(query_spec, api_key, project_id)
        LOGGER.info("processing query %s -> %s", query_name, output_file)
        LOGGER.info("request url for %s: %s", query_name, mask_logged_url(url, api_key, project_id))
        if dry_run:
            LOGGER.info("dry run only; request not sent")
        else:
            download_csv(url, output_file)
            LOGGER.info("saved %s", output_file)
        downloaded_files.append(output_file)
    return downloaded_files


def run_follow_up_command(script_relative_path, script_args, dry_run=False):
    command = [sys.executable, os.path.normpath(os.path.join(SCRIPT_FOLDER, script_relative_path))]
    command.extend(script_args)
    LOGGER.info("running follow-up command: %s", " ".join(command))
    if dry_run:
        LOGGER.info("dry run only; follow-up command not run")
        return
    subprocess.run(command, check=True)


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

        config = load_json_file(args.secrets_path)
        api_key = get_secret_value(ENV_API_KEY, config, ENV_API_KEY, "API_KEY")
        project_id = get_secret_value(ENV_PROJECT_ID, config, ENV_PROJECT_ID, "Project_ID")
        query_specs = get_query_specs(config)
        if args.query_names:
            missing_queries = [name for name in args.query_names if name not in query_specs]
            if missing_queries:
                raise ValueError("unknown query names: {}".format(", ".join(sorted(missing_queries))))
            query_specs = {name: query_specs[name] for name in args.query_names}
        else:
            default_query_names = get_default_query_names(query_specs)
            query_specs = {name: query_specs[name] for name in default_query_names}

        if args.list_queries:
            for query_name in sorted(get_query_specs(config)):
                print(query_name)
            return

        if args.no_import:
            LOGGER.info("--no-import set; skipping Trap.NZ API calls")
        else:
            run_imports(args.output_folder, query_specs, api_key, project_id, dry_run=args.dry_run)
        if args.merge_recent:
            run_follow_up_command(TRANSFORM_SCRIPT, ["--merge_recent"], dry_run=args.dry_run)
        if args.publish:
            run_follow_up_command(PUBLISH_SCRIPT, [], dry_run=args.dry_run)
    finally:
        if initial_wd != base_folder:
            os.chdir(initial_wd)


if __name__ == "__main__":
    main()
