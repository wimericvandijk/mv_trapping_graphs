import argparse
import csv
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
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
DEFAULT_OUTPUT_FILE = "../../data/raw/bird-sightings-api.csv"
PUBLISH_SCRIPT = "../publish/publish_to_json.py"
ENV_SERVICE_ACCOUNT_FILE = "BIRD_GOOGLE_SERVICE_ACCOUNT_FILE"
ENV_SPREADSHEET_ID = "BIRD_SHEETS_SPREADSHEET_ID"
ENV_SHEET_RANGE = "BIRD_SHEETS_RANGE"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
SHEETS_VALUES_URL_TEMPLATE = "https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_range}?majorDimension=ROWS"
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
}


def get_cmd_args(title):
    parser = argparse.ArgumentParser(title)
    parser.add_argument(
        "-sp",
        "--secrets_path",
        help="path to the ignored local secrets file",
        default=DEFAULT_SECRETS_PATH,
    )
    parser.add_argument(
        "--service-account-file",
        help="path to the Google service account JSON file",
    )
    parser.add_argument(
        "--spreadsheet-id",
        help="Google Sheets spreadsheet ID",
    )
    parser.add_argument(
        "--sheet-range",
        help="A1 notation range to fetch, for example 'Form Responses 1'!A:G",
    )
    parser.add_argument(
        "-of",
        "--output_file",
        help="path to save the imported bird CSV file",
        default=DEFAULT_OUTPUT_FILE,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="log the request that would run without making network requests",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="run publish_to_json.py after a successful bird import",
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


def get_secret_value(explicit_value, env_name, config, *config_keys):
    if explicit_value not in {None, ""}:
        return explicit_value
    env_value = os.getenv(env_name)
    if env_value not in {None, ""}:
        return env_value
    for key in config_keys:
        value = config.get(key)
        if value not in {None, ""}:
            return value
    return None


def ensure_parent_folder(path):
    Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
    return path


def load_google_auth_dependencies():
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except ImportError as exc:
        raise RuntimeError(
            "Google authentication dependencies are not installed. Run 'pip install google-auth' and try again."
        ) from exc
    return GoogleAuthRequest, service_account


def get_access_token(service_account_file):
    google_auth_request_cls, service_account = load_google_auth_dependencies()
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=[SHEETS_SCOPE],
    )
    credentials.refresh(google_auth_request_cls())
    return credentials.token


def build_values_url(spreadsheet_id, sheet_range):
    encoded_range = quote(sheet_range, safe="!:$,'")
    return SHEETS_VALUES_URL_TEMPLATE.format(
        spreadsheet_id=spreadsheet_id,
        sheet_range=encoded_range,
    )


def fetch_sheet_values(spreadsheet_id, sheet_range, access_token):
    url = build_values_url(spreadsheet_id, sheet_range)
    headers = dict(DEFAULT_REQUEST_HEADERS)
    headers["Authorization"] = "Bearer {}".format(access_token)
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        payload = response.read()
    response_json = json.loads(payload.decode("utf-8"))
    return response_json.get("values", [])


def write_values_to_csv(values, output_file):
    if not values:
        raise ValueError("no rows returned from Google Sheets API")

    header = [str(value).strip() for value in values[0]]
    if not any(header):
        raise ValueError("the first row from Google Sheets API is empty")

    rows = values[1:]
    output_path = ensure_parent_folder(output_file)
    with open(output_path, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for raw_row in rows:
            padded_row = list(raw_row) + [""] * max(0, len(header) - len(raw_row))
            writer.writerow({header[index]: padded_row[index] for index in range(len(header))})
    return output_path, len(rows)


def mask_spreadsheet_id(spreadsheet_id):
    if not spreadsheet_id or len(spreadsheet_id) <= 8:
        return "<spreadsheet_id>"
    return "{}...{}".format(spreadsheet_id[:4], spreadsheet_id[-4:])


def run_publish_script():
    command = [sys.executable, PUBLISH_SCRIPT]
    LOGGER.info("running publish step: %s", " ".join(command))
    subprocess.run(command, cwd=SCRIPT_FOLDER, check=True)


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
        service_account_file = get_secret_value(
            args.service_account_file,
            ENV_SERVICE_ACCOUNT_FILE,
            config,
            ENV_SERVICE_ACCOUNT_FILE,
        )
        spreadsheet_id = get_secret_value(
            args.spreadsheet_id,
            ENV_SPREADSHEET_ID,
            config,
            ENV_SPREADSHEET_ID,
        )
        sheet_range = get_secret_value(
            args.sheet_range,
            ENV_SHEET_RANGE,
            config,
            ENV_SHEET_RANGE,
        )

        if not service_account_file:
            raise ValueError(
                "Google service account file is required. Set BIRD_GOOGLE_SERVICE_ACCOUNT_FILE, add it to the ignored secrets file, or pass --service-account-file."
            )
        if not spreadsheet_id:
            raise ValueError(
                "Google spreadsheet ID is required. Set BIRD_SHEETS_SPREADSHEET_ID, add it to the ignored secrets file, or pass --spreadsheet-id."
            )
        if not sheet_range:
            raise ValueError(
                "Google sheet range is required. Set BIRD_SHEETS_RANGE, add it to the ignored secrets file, or pass --sheet-range."
            )

        values_url = build_values_url(spreadsheet_id, sheet_range)
        LOGGER.info(
            "prepared Google Sheets request for spreadsheet %s and range %s",
            mask_spreadsheet_id(spreadsheet_id),
            sheet_range,
        )
        LOGGER.debug("request url: %s", values_url)

        if args.dry_run:
            LOGGER.info("dry run only; request not sent")
            return

        access_token = get_access_token(service_account_file)
        values = fetch_sheet_values(spreadsheet_id, sheet_range, access_token)
        output_path, row_count = write_values_to_csv(values, args.output_file)
        LOGGER.info("saved %d bird rows to %s", row_count, output_path)

        if args.publish:
            run_publish_script()
    finally:
        if initial_wd != base_folder:
            os.chdir(initial_wd)


if __name__ == "__main__":
    main()