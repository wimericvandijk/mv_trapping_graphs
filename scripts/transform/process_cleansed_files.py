import argparse
import logging
import os
import sys

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)
SCRIPTS_FOLDER = os.path.dirname(SCRIPT_FOLDER)
if SCRIPTS_FOLDER not in sys.path:
    sys.path.insert(0, SCRIPTS_FOLDER)

from script_logging import configure_script_logging


LOGGER = logging.getLogger()


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
        help="future folder for processed outputs such as parquet",
        default="../../data/processed",
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
        LOGGER.info("stub only: no processed outputs are created yet")
    finally:
        if initial_wd != base_folder:
            os.chdir(initial_wd)


if __name__ == "__main__":
    main()