"""
Simple analysis of trap distances from each other.  Of course that depands on how good the coordinate data is.
"""
import argparse

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from bisect import insort, bisect_left, bisect_right
import csv
from glob import glob
import json
import logging
from statistics import mean
import os
from pprint import pformat
import sys

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)
SCRIPTS_FOLDER = os.path.dirname(SCRIPT_FOLDER)
if SCRIPTS_FOLDER not in sys.path:
    sys.path.insert(0, SCRIPTS_FOLDER)

from script_logging import configure_script_logging

import pandas as pd
import numpy as np

from domain_constants import SPECIES_CAT
from domain_constants import SPECIES_HEDGEHOG
from domain_constants import SPECIES_MOUSE
from domain_constants import SPECIES_NONE
from domain_constants import SPECIES_OTHER
from domain_constants import SPECIES_POSSUM
from domain_constants import SPECIES_RAT
from domain_constants import SPECIES_STOAT
from domain_constants import SPECIES_WEASEL
from domain_constants import TRAP_TYPE_DOC_200 as CANONICAL_TRAP_TYPE_DOC_200
from domain_constants import TRAP_TYPE_POSSUM_MASTER as CANONICAL_TRAP_TYPE_POSSUM_MASTER
from domain_constants import TRAP_TYPE_TRAPINATOR as CANONICAL_TRAP_TYPE_TRAPINATOR
from domain_constants import TRAP_TYPE_VICTOR as CANONICAL_TRAP_TYPE_VICTOR

LOGGER = logging.getLogger()

FIELD_RETIRED = "Retired"
FIELD_LINE = "line"
FIELD_LAT = "latitude"
FIELD_LON = "longitude"
FIELD_CODE = "code"
FIELD_DATE = "date"
FIELD_SPECIES = "species caught"
FIELD_TRAP_TYPE = "trap type"


CATCH_ANY = "Any"
FIELD_TIMESTAMPS = "timestamps"

FIELDS_NUMERIC = {FIELD_LAT, FIELD_LON}
REQUIRED_FIELDS = [
    FIELD_DATE,
    FIELD_LINE,
    FIELD_LAT,
    FIELD_LON,
    FIELD_TRAP_TYPE,
    FIELD_CODE,
    FIELD_SPECIES,
]

CATCH_TYPE_MOUSE = SPECIES_MOUSE
CATCH_TYPE_RAT = SPECIES_RAT
# CATCH_TYPE_RAT_NORWAY = "Rat - Norway"
# CATCH_TYPE_RAT_SHIP = "Rat - Ship"
CATCH_TYPE_POSSUM = SPECIES_POSSUM
CATCH_TYPE_STOAT = SPECIES_STOAT
CATCH_TYPE_WEASEL = SPECIES_WEASEL
CATCH_TYPE_CAT = SPECIES_CAT
CATCH_TYPE_HEDGEHOG = SPECIES_HEDGEHOG
CATCH_TYPE_OTHER = SPECIES_OTHER
CATCH_TYPE_ANY = CATCH_ANY
CATCH_TYPE_NONE = SPECIES_NONE

CATCH_TYPES = [
    CATCH_TYPE_MOUSE,
    CATCH_TYPE_RAT,
    CATCH_TYPE_POSSUM,
    CATCH_TYPE_STOAT,
    CATCH_TYPE_WEASEL,
    CATCH_TYPE_CAT,
    CATCH_TYPE_HEDGEHOG,
    CATCH_TYPE_OTHER,
]

JSON_EXT = ".json"

CODE_LINE_LOOKUP = {
    "BN": "Barnicoat North",
    "BS": "Barnicoat South",
    "JK": "JK",
    "LR": "Lima Ridge",
    # 'MC': '',
    "NB": "NBS",
    # 'OV': '',
    # 'SV': '',
    # 'WI': ''
}
TRAP_TYPE_DOC200 = CANONICAL_TRAP_TYPE_DOC_200
TRAP_TYPE_VICTOR = CANONICAL_TRAP_TYPE_VICTOR
TRAP_TYPE_TRAPINATOR = CANONICAL_TRAP_TYPE_TRAPINATOR
TRAP_TYPE_POSSUM_MASTER = CANONICAL_TRAP_TYPE_POSSUM_MASTER
TRAP_TYPE_LOOKUP = {
    CATCH_TYPE_RAT: [TRAP_TYPE_DOC200, TRAP_TYPE_VICTOR],
    CATCH_TYPE_POSSUM: [TRAP_TYPE_TRAPINATOR, TRAP_TYPE_POSSUM_MASTER],
    CATCH_TYPE_MOUSE: [TRAP_TYPE_DOC200, TRAP_TYPE_VICTOR],
}
LINE_NAMES_ALL = []
ACTIVE = "Active"

TIMESTAMP_FMT = "%Y-%m-%d"  # "2024-02-11"
CATCH_FRACTION_METRIC = "get_catch_fraction"
CATCH_COUNT_METRIC = "get_catch_count"

POINT_LL_CEMETERY = (-41.31807039623798, 173.25188015037233)
POINT_LL_ROAD_END = (-41.3285699010029, 173.26416365530244)
POINT_LL_SANCTUARY = (-41.32406951809612, 173.25808280684493)
POINT_LL_RESERVE = (-41.32596564790335, 173.2621341040978)
POINT_LLS = {
    "cemetery": POINT_LL_CEMETERY,
    "road_end": POINT_LL_ROAD_END,
    "sanctuary": POINT_LL_SANCTUARY,
    "reserve": POINT_LL_RESERVE,
}

CLIMATE_DATE_COL = "Date"
CLIMATE_RAIN_COL = "Rainfall [mm]"
CLIMATE_TEMPERATURE_COL = "Mean Temperature [Deg C]"


def insert_in_sorted_list_if_missing(item, sorted_list):
    index = bisect_left(sorted_list, item)
    if index != len(sorted_list) and sorted_list[index] == item:
        return sorted_list
    sorted_list.insert(index, item)
    return sorted_list


def str_is_time_format(timestamp, fmt):
    try:
        dt = datetime.strptime(timestamp, fmt)
        return True, dt
    except ValueError:
        return False, None


def decode_date_to_timestamp(cell_value):
    timestamp = cell_value[:10].strip()
    is_time_fmt, dt = str_is_time_format(timestamp, TIMESTAMP_FMT)
    if is_time_fmt:
        return dt_to_timestamp(dt)
    is_time_fmt, dt = str_is_time_format(timestamp, "%d/%m/%Y")
    if is_time_fmt:
        return dt_to_timestamp(dt)
        return None


def haversine_metres(lat1, lon1, lat2, lon2):
    """returns distance in metres between two locations"""
    from math import radians, sin, cos, asin, sqrt

    earth_radius_metres = 6372800  # 6372.8 km

    lat_diff = radians(lat2 - lat1)
    lon_diff = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(lat_diff / 2) ** 2 + cos(lat1) * cos(lat2) * sin(lon_diff / 2) ** 2
    c = 2 * asin(sqrt(a))

    return earth_radius_metres * c


def bisect_indexof(sorted_list, item):
    result = bisect_left(sorted_list, item)
    if result < 0 or result >= len(sorted_list):
        return -1
    if sorted_list[result] == item:
        return result
    return -1


def dt_to_timestamp(dt):
    return dt.strftime(TIMESTAMP_FMT)


CTT_T_NAMES = {
    "get_catch_count": "Catch count",
    "get_number_traps": "Number of traps",
    "get_mean_trap_spacing": "Average trap spacing",
    "get_mean_checks_per_trap": "Average checks per trap",
    "get_mean_distance_from_nearest_road": "Average distance from road",
    "get_catch_fraction": "Fraction of total catches",
}
CTT_T_NAME_NO_STATS = ["get_catch_count"]


def get_cut_down_df(df, year, month_fromto):
    month_from, month_to = month_fromto.split("|")
    start_timestamp = "{}-{}".format(year, month_from)
    finish_timestamp = "{}-{}".format(year, month_to)
    date_col = df[CLIMATE_DATE_COL]
    return df[(start_timestamp < date_col) & (date_col < finish_timestamp)]


def get_df_data(filename, key_field, start, finish):
    """
    We want df[key_field] for 24 hours (df['PERIOD [hrs]']) prior to df['Date']
    Assume period is always 24 and the observation is taken at 9am the next day.
    Format of Observation time is %Y-%m-%dT%H:%M%SZ, 1981-12-31T20:00:00Z and for Date is %Y-%m-%d, 1981-12-31
    Filter to start < Date < finish where start and finish are in %Y-%m-%d format

    Args:
        filename: str
        key_field: str
        start: dt
        finish: dt

    Returns: dataframe

    """
    if not os.path.exists(filename):
        return {}
    df = pd.read_excel(filename)
    # CLIMATE_DATE_COL = 'Date'
    # CLIMATE_RAIN_COL = 'Rainfall [mm]'
    # CLIMATE_TEMPERATURE_COL = 'Mean Temperature [Deg C]'
    columns_to_drop = sorted(set(df.columns) - {CLIMATE_DATE_COL, key_field})
    df = df.drop(columns_to_drop, axis=1)
    start_timestamp = start.strftime("%Y-%m-%d")
    finish_timestamp = finish.strftime("%Y-%m-%d")
    result = df[
        (start_timestamp < df[CLIMATE_DATE_COL])
        & (df[CLIMATE_DATE_COL] < finish_timestamp)
    ]
    # result = {}
    # dates = filtered[CLIMATE_DATE_COL].values
    # rainfalls = filtered[key_field].values
    # for idx, date in enumerate(dates):
    #     result[date] = rainfalls[idx]
    LOGGER.info(
        "Read %d %s observations (%s - %s)",
        len(result),
        key_field,
        start_timestamp,
        finish_timestamp,
    )
    return result


class Line:
    def __init__(self, name):
        self.name = name
        self.timestamp_catches = defaultdict(dict)
        self.timestamps = []

    def add_catch(self, timestamp, data):
        code = data[FIELD_CODE]
        self.timestamp_catches[timestamp][code] = Trap(data)

    def set_and_sort_timestamps(self):
        self.timestamps = sorted(self.timestamp_catches)

    def get_timestamps_between(
        self, timestamp_from, timestamp_to, can_catch_types=None
    ):
        return self.timestamps[
            bisect_left(self.timestamps, timestamp_from) : bisect_right(
                self.timestamps, timestamp_to
            )
        ]

    def get_timestamps_between_that_can_catch(
        self, timestamp_from, timestamp_to, can_catch_types
    ):
        result = defaultdict(list)
        for timestamp in self.get_timestamps_between(timestamp_from, timestamp_to):
            for trap in self.timestamp_catches[timestamp].values():
                if trap.get_can_catch(can_catch_types):
                    result[timestamp].append(trap)
        return dict(result)

    def get_catch_count(self, catch_types, timestamp_from, timestamp_to):
        result = None
        for timestamp in self.get_timestamps_between(timestamp_from, timestamp_to):
            for trap in self.timestamp_catches[timestamp].values():
                if result is None:
                    result = trap.get_catch_count(catch_types)
                else:
                    result += trap.get_catch_count(catch_types)
        return result

    def get_catch_count_fraction(
        self, catch_types, timestamp_from, timestamp_to, total_count
    ):
        if total_count is None or total_count <= 0:
            return None
        catch_count = self.get_catch_count(catch_types, timestamp_from, timestamp_to)
        if catch_count is None:
            return None
        return round(catch_count / total_count, 4)

    def get_number_traps(self, catch_types, timestamp_from, timestamp_to):
        timestamp_traps = self.get_timestamps_between_that_can_catch(
            timestamp_from, timestamp_to, catch_types
        )
        codes = set()
        for traplist in timestamp_traps.values():
            for trap in traplist:
                codes.add(trap.code)
        return len(codes)

    def get_mean_trap_spacing(self, catch_types, timestamp_from, timestamp_to):
        spacings = []
        timestamp_traps = self.get_timestamps_between_that_can_catch(
            timestamp_from, timestamp_to, catch_types
        )
        for timestamp, traplist in timestamp_traps.items():
            spacing = self.get_mean_spacing_for(traplist)
            if spacing:
                spacings.append(spacing)
        if spacings:
            return round(mean(spacings), 4)
        return None

    def get_mean_spacing_for(self, traps):
        spacings = []
        already_done = set()
        for trap in traps:
            tup = self.get_spacing(trap, traps, already_done)
            spacing, already_done = tup
            if spacing:
                spacings.append(spacing)
        return mean(spacings) if spacings else None

    def get_spacing(self, trap, traps, already_done):
        spacings = []
        for trap1 in traps:
            if trap1.code == trap.code:
                continue
            tkn = ",".join(sorted([trap.code, trap1.code]))
            if tkn not in already_done:
                spacings.append(trap.get_metres_apart(trap1))
                already_done.add(tkn)
        if not spacings:
            return None, already_done
        return min(spacings), already_done

    def get_mean_checks_per_trap(self, catch_types, timestamp_from, timestamp_to):
        timestamp_traps = self.get_timestamps_between_that_can_catch(
            timestamp_from, timestamp_to, catch_types
        )
        if not timestamp_traps:
            return None
        code_timestamps = defaultdict(set)
        for timestamp, traplist in timestamp_traps.items():
            for trap in traplist:
                code_timestamps[trap.code].add(timestamp)
        result = sum(
            [len(timestamps) for timestamps in code_timestamps.values()]
        ) / len(code_timestamps)
        return round(result, 4)

    def get_mean_distance_from_nearest_road(
        self, catch_types, timestamp_from, timestamp_to
    ):
        result = None
        for _name, point_ll in POINT_LLS.items():
            mean_distance_from_point = self.get_mean_distance_from_point(
                catch_types, timestamp_from, timestamp_to, point_ll
            )
            if mean_distance_from_point is not None:
                result = (
                    mean_distance_from_point
                    if result is None
                    else min(result, mean_distance_from_point)
                )
        return result

    def get_mean_distance_from_point(
        self, catch_types, timestamp_from, timestamp_to, point_ll
    ):
        code_dist = {}
        timestamp_traps = self.get_timestamps_between_that_can_catch(
            timestamp_from, timestamp_to, catch_types
        )
        for trap_list in timestamp_traps.values():
            for trap in trap_list:
                if trap.code not in code_dist:
                    code_dist[trap.code] = trap.get_metres_from(
                        point_ll[0], point_ll[1]
                    )
        if not code_dist:
            return None
        return round(mean([dist for dist in code_dist.values()]), 4)


class Traps:
    def __init__(self):
        super().__init__()
        self.lines = {}
        self.rain_df = None
        self.temperature_df = None

    def read_data(self, path, line_names):
        """

        Args:
            path:
            line_names:

        Returns: number of data lines ingested

        """
        filenames = glob("{}/*.csv".format(path))
        result = 0
        for filename in filenames:
            with open(filename, "r", newline="") as fp:
                reader = csv.reader(fp)
                header = next(reader)
                missing = set(REQUIRED_FIELDS) - set(header)
                if missing:
                    LOGGER.warning(
                        'missing %s in header "%s" - ignoring %s',
                        missing,
                        header,
                        filename,
                    )
                    continue
                for row_index, row in enumerate(reader):
                    if len(row) < len(header):
                        LOGGER.warning(
                            "row[%d] only has %d columns but header has %d - ignoring",
                            row_index + 1,
                            len(row),
                            len(header),
                        )
                        continue

                    data = {
                        field_name: row[idx] for idx, field_name in enumerate(header)
                    }
                    line_name = data[FIELD_LINE]
                    if not line_name:
                        code_prefix = data.get(FIELD_CODE, "")[:2]
                        line_name = CODE_LINE_LOOKUP.get(code_prefix, "")
                    if line_names and line_name not in line_names:
                        LOGGER.debug(
                            'row[%d] line "%s" not in required lines - ignoring',
                            row_index + 1,
                            line_name,
                        )
                        continue
                    timestamp = decode_date_to_timestamp(data[FIELD_DATE])
                    if not timestamp:
                        LOGGER.warning(
                            'row[%d] date "%s" could not be decoded - ignoring',
                            row_index + 1,
                            data[FIELD_DATE],
                        )
                        continue
                    self.add_catch(line_name, timestamp, data)
                    result += 1
        for _line_name, line in self.lines.items():
            line.set_and_sort_timestamps()
        return result

    def add_catch(self, line_name, timestamp, data):
        """
        loads a trap record
        Args:
            line_name: str
            timestamp: str
            data: {}

        Returns:

        """

        if not timestamp:
            LOGGER.warning("Traps.add_catch missing timestamp - ignoring")
            return
        if not data:
            LOGGER.warning("Traps.add_catch missing data - ignoring")
            return
        if not line_name:
            LOGGER.debug(
                "Traps.add_catch missing line - will add this %s record to blank Line",
                data.get(FIELD_CODE),
            )
            line_name = ""
        if line_name not in self.lines:
            self.lines[line_name] = Line(line_name)
        self.lines[line_name].add_catch(timestamp, data)

    def get_total_catch_count(self, catch_types, timestamp_from, timestamp_to):
        result = 0
        for _line_name, line in self.lines.items():
            catch_count = line.get_catch_count(
                catch_types, timestamp_from, timestamp_to
            )
            if catch_count:
                result += catch_count
        return result

    def get_ctt_outputs(
        self, start, finish, interval_months, catch_types, output_file=None
    ):
        method_names = get_ctt_line_method_names()
        result = {}
        dt_from = start
        dt_to = add_months_to(dt_from, interval_months)
        dt_to -= timedelta(days=1)
        if isinstance(catch_types, str):
            catch_types = [catch_types]
        while (dt_from < finish) and (dt_from < dt_to):
            timestamp_from = dt_to_timestamp(dt_from)
            timestamp_to = dt_to_timestamp(dt_to)
            interval_stamp = "{}|{}".format(timestamp_from, timestamp_to)
            total_catches = self.get_total_catch_count(
                catch_types, timestamp_from, timestamp_to
            )
            for line_name, line in self.lines.items():
                for method_name in method_names:
                    method = getattr(line, method_name)
                    value = method(catch_types, timestamp_from, timestamp_to)
                    if line_name not in result:
                        result[line_name] = {}
                    if interval_stamp not in result[line_name]:
                        result[line_name][interval_stamp] = {}
                    result[line_name][interval_stamp][method_name] = value
                    if method_name == "get_catch_count":

                        if total_catches and value is not None:
                            catch_fraction = round(value / total_catches, 4)
                        else:
                            catch_fraction = None
                        result[line_name][interval_stamp][
                            "get_catch_fraction"
                        ] = catch_fraction
            dt_from = dt_to + timedelta(days=1)  # next day
            dt_to = add_months_to(dt_from, interval_months)
            dt_to -= timedelta(days=1)
            if dt_to > finish:
                dt_to = finish
        if output_file:
            save_json(result, output_file, log_it=True)
        return result

    def get_datestamps(self, json_data):
        result = set()
        for _line_name, datestamp_data in json_data.items():
            for datestamp in datestamp_data:
                result.add(datestamp)
        return sorted(result)

    def get_metrics(self, json_data, key_metric):
        for line_name in sorted(json_data):
            if not line_name:
                continue
            datestamp_data = json_data[line_name]
            for datestamp, data in datestamp_data.items():
                if key_metric not in data:
                    raise ValueError(
                        "key metric {} is not in {}".format(
                            key_metric, [d for d in data]
                        )
                    )
                result = {metric: {} for metric in sorted(data)}
            return result
        return None

    def get_correlations(self, json_file, key_metric, csv_filename):
        json_data = load_json(json_file)
        metric_data = self.get_metrics(json_data, key_metric)
        if metric_data is None:
            raise ValueError("no metrics found in {}".format(json_file))

        csv_lines = [
            ",".join(
                ["Line", "datestamp"] + [metric_tidied(m) for m in sorted(metric_data)]
            )
        ]
        for line_name in sorted(json_data):
            if not line_name:
                continue
            datestamp_data = json_data[line_name]
            for datestamp, data in datestamp_data.items():
                csv_line_list = [line_name, datestamp]
                have_key_data = False
                for metric in sorted(metric_data):
                    key = "{}|{}".format(line_name, datestamp)
                    value = data.get(metric, None)
                    metric_data[metric][key] = value
                    value_str = "" if value is None else "{}".format(round(value, 4))
                    csv_line_list.append(value_str)
                    if metric == key_metric and value_str:
                        have_key_data = True
                if have_key_data:
                    csv_lines.append(",".join(csv_line_list))
        key_metric_keys = [key for key in sorted(metric_data[key_metric])]
        key_metric_list = [metric_data[key_metric][key] for key in key_metric_keys]
        key_metric_series = pd.Series(key_metric_list)
        lines = []

        for metric in sorted(metric_data):
            if metric == key_metric or metric in CTT_T_NAME_NO_STATS:
                continue  # already have this
            metric_list = [metric_data[metric].get(key) for key in key_metric_keys]
            corr = round(pd.Series(metric_list).corr(key_metric_series), 4)
            lines.append("{:30} {}".format(metric_tidied(metric), corr))
        if csv_filename:
            with open(csv_filename, "w") as fp:
                fp.write("\n".join(csv_lines))
            LOGGER.info("saved %s", csv_filename)
        return lines

    def get_total_rain(self, year, month_fromto, default):
        df = get_cut_down_df(self.rain_df, year, month_fromto)
        if df.empty:
            return default
        result = int(round(df[CLIMATE_RAIN_COL].sum()))
        return result

    def get_mean_temperature(self, year, month_fromto, default):
        df = get_cut_down_df(self.temperature_df, year, month_fromto)
        if df.empty:
            return default
        result = int(round(df[CLIMATE_TEMPERATURE_COL].mean()))
        return result

    def get_seasonality_lines(
        self,
        json_file,
        catch_count_metric,
        start_timestamp,
        finish_timestamp,
        month_interval,
        csv_filename,
        catch_type
    ):
        """

        Args:
            json_file: {line_name: {"yyyy-mm-dd|yyyy-mm-dd": {metric: value, }}}
            catch_count_metric: str
            start_timestamp: str
            finish_timestamp: str
            month_interval: int
            csv_filename: str

        Returns: [str]

        """
        json_data = load_json(json_file)
        datestamps = self.get_datestamps(json_data)

        def get_year_monthfromto(ds_):
            year = ds_[:4]
            from_ = ds_[5:10]
            to_ = ds_[16:21]
            if to_ == "02-29":  # leap year
                to_ = "02-28"
            return year, "{}|{}".format(from_, to_)

        years = set()
        monthfromtos = set()
        for datestamp in datestamps:
            year, monthfromto = get_year_monthfromto(
                datestamp
            )  # todo ignore leap year in title?
            years.add(year)
            monthfromtos.add(monthfromto)
        years = sorted(years)
        monthfromtos = sorted(monthfromtos)

        years_month_fromto_count = defaultdict(dict)
        for year in years:
            for monthfromto in monthfromtos:
                years_month_fromto_count[year][monthfromto] = 0

        for line_name, datestamp_data in json_data.items():
            for datestamp, data in datestamp_data.items():
                year, monthfromto = get_year_monthfromto(datestamp)
                count = data.get(catch_count_metric, 0)
                years_month_fromto_count[year][monthfromto] += 0 if not count else count

        csv_lines = [",".join(["Year", "measure"] + monthfromtos)]
        corr_data = {}
        for year in sorted(years_month_fromto_count):
            # Catches
            csv_line = [year, "catches"]
            month_fromto_count = years_month_fromto_count[year]
            for month_fromto in sorted(month_fromto_count):
                count = month_fromto_count.get(month_fromto, 0)
                csv_line.append(count)
                corr_data['{}{}'.format(year, month_fromto[:2])] = {'catches': count}
            csv_lines.append(",".join(["{}".format(cell) for cell in csv_line]))

            # Rain
            if self.rain_df is not None and not self.rain_df.empty:
                csv_line = [year, "rain"]
                for month_fromto in sorted(month_fromto_count):
                    total_rain = self.get_total_rain(year, month_fromto, 0)
                    csv_line.append(str(total_rain))
                    corr_data['{}{}'.format(year, month_fromto[:2])]['rain'] = total_rain
                csv_lines.append(",".join(["{}".format(cell) for cell in csv_line]))
            # Temperature
            if self.rain_df is not None and not self.rain_df.empty:
                csv_line = [year, "temperature"]
                for month_fromto in sorted(month_fromto_count):
                    average_temp = self.get_mean_temperature(year, month_fromto, 0)
                    csv_line.append(str(average_temp))
                    corr_data['{}{}'.format(year, month_fromto[:2])]['temperature'] = average_temp
                csv_lines.append(",".join(["{}".format(cell) for cell in csv_line]))
        if csv_filename:
            with open(csv_filename, "w") as fp:
                fp.write("\n".join(csv_lines))
            LOGGER.info("saved %s", csv_filename)
            root, basename = os.path.split(csv_filename)
            climate_csv_filename = '{}/{}_climate.csv'.format(root, basename.replace('.csv', ''))
            get_climate_correlation_and_save_csv(catch_type, corr_data, climate_csv_filename)

        return csv_lines

def get_climate_correlation_and_save_csv(catch_type, corr_data, climate_csv_filename):
    csv_lines = ['date,catches,rain,temperature']
    catches_list = []
    rain_list = []
    temp_list = []
    for date in sorted(corr_data):
        catches = corr_data[date]['catches']
        rain = corr_data[date]['rain']
        temperature = corr_data[date]['temperature']
        csv_lines.append('{},{},{},{}'.format(date, catches, rain, temperature))
        catches_list.append(catches)
        rain_list.append(rain)
        temp_list.append(temperature)
    with open(climate_csv_filename, "w") as fp:
        fp.write("\n".join(csv_lines))
    LOGGER.info("saved %s", climate_csv_filename)
    rain_corr = round(pd.Series(rain_list).corr(pd.Series(catches_list)), 4)
    LOGGER.info('Rain correlation for %s = %s', catch_type, rain_corr)
    temp_corr = round(pd.Series(temp_list).corr(pd.Series(catches_list)), 4)
    LOGGER.info('Temperature correlation for %s = %s', catch_type, temp_corr)
    return rain_corr, temp_corr, csv_lines

def metric_tidied(metric):
    result = CTT_T_NAMES.get(metric)
    if result:
        return result

    return metric.replace("get_", "").replace("_", " ")


def add_month_to(dt_from):
    day_in_result = dt_from.day
    if day_in_result > 28:
        raise ValueError("add_months_to day cannot be > 28")
    current_month = dt_from.month
    result = dt_from
    while result.month == current_month:
        result += timedelta(days=10)
    return datetime(result.year, result.month, day_in_result)


def add_months_to(dt_from, interval_months):
    result = dt_from
    for month_count in range(interval_months):
        result = add_month_to(result)
    return result


def get_ctt_line_method_names():
    result = []
    for method in vars(Line):
        if callable(getattr(Line, method)) and method in CTT_T_NAMES:
            result.append(method)
    return result


class Trap:
    def __init__(self, data):  # constructor
        self.code = data.get(FIELD_CODE, "")
        self.data = data

    def get_catch_count(self, catch_types):
        species = self.data[FIELD_SPECIES]
        if not species or species == "None":
            return 0
        if any(species.startswith(catch_type) for catch_type in catch_types):
            return 1
        return 0

    def get_can_catch(self, catch_types):
        trap_type = self.data[FIELD_TRAP_TYPE]
        for catch_type in catch_types:
            if trap_type in TRAP_TYPE_LOOKUP.get(catch_type, []):
                return True
        return False

    def get_metres_apart(self, trap):
        return self.get_metres_from(
            float(trap.data[FIELD_LAT]), float(trap.data[FIELD_LON])
        )

    def get_metres_from(self, latitude, longitude):
        return haversine_metres(
            float(self.data[FIELD_LAT]),
            float(self.data[FIELD_LON]),
            latitude,
            longitude,
        )


def load_json(filename, default=None):
    try:
        with open(filename) as fp:
            return json.load(fp)
    except Exception:
        return default


def save_json(obj, filename, load_existing=False, log_it=True):
    if not filename.lower().endswith(JSON_EXT):
        filename += JSON_EXT
    if load_existing:
        data = load_json(filename, {})
        if not data:
            data = obj
        else:
            data.update(obj)
    else:
        data = obj
    with open(filename, "w") as fp:
        json.dump(data, fp, indent=4, sort_keys=True)
    if log_it:
        LOGGER.info("Saved JSON file %s", os.path.realpath(filename))


def get_cmd_args(title):
    """

    Returns: argParse object

    """
    parser = argparse.ArgumentParser(title)

    parser.add_argument(
        "-p", "--path", help="path to csv folder", default="./data",
    )
    parser.add_argument(
        "-rf", "--rain_file", help="path to rain file", default=None,
    )
    parser.add_argument(
        "-tf", "--temperature_file", help="path to temperature file", default=None,
    )
    parser.add_argument(
        "-ln",
        "--line_name",
        nargs="*",
        default=LINE_NAMES_ALL,
        help="only look at these lines",
    )
    parser.add_argument(
        "--start",
        default="2020-01-01",
        help="start timestamp as {}".format(TIMESTAMP_FMT),
    )  # "%Y-%m-%d"
    parser.add_argument(
        "--finish",
        default="2025-12-12",
        help="finish timestamp as {}".format(TIMESTAMP_FMT),
    )
    parser.add_argument("--interval", default=3, type=int, help="month interval")

    parser.add_argument(
        "--use_cache",
        default=False,
        action="store_true",
        help="do not re-read and recreate data",
    )
    return parser.parse_args()


def main():
    """main program"""
    base_folder = SCRIPT_FOLDER
    base_filename_only, _ext = os.path.splitext(os.path.basename(__file__))
    initial_wd = os.getcwd()
    if initial_wd != base_folder:
        os.chdir(base_folder)
    try:
        args = get_cmd_args(base_filename_only)
        configure_script_logging(LOGGER, SCRIPT_PATH)
        LOGGER.info("args: %s", args)
        LOGGER.info("cwd: %s", os.getcwd())

        traps = Traps()

        catch_types = [CATCH_TYPE_RAT, CATCH_TYPE_POSSUM, CATCH_TYPE_MOUSE]
        start = datetime.strptime(args.start, TIMESTAMP_FMT)
        finish = datetime.strptime(args.finish, TIMESTAMP_FMT)
        interval = args.interval

        # ingest data
        LOGGER.info("reading rain data from %s", args.rain_file)
        traps.rain_df = get_df_data(args.rain_file, CLIMATE_RAIN_COL, start, finish)
        LOGGER.info("reading temperature data from %s", args.temperature_file)
        traps.temperature_df = get_df_data(
            args.temperature_file, CLIMATE_TEMPERATURE_COL, start, finish
        )

        LOGGER.info("ingesting csv data")
        record_count = traps.read_data(args.path, line_names=args.line_name)
        LOGGER.info("read %d records", record_count)

        json_files_stats = {
            catch_type: "data/output_stat_{}_{}_to_{}_{}_monthly{}".format(
                catch_type, args.start, args.finish, interval, JSON_EXT
            )
            for catch_type in catch_types
        }
        _json_files_seasonality = {
            catch_type: "data/output_season_{}_{}_to_{}_{}_monthly{}".format(
                catch_type, args.start, args.finish, interval, JSON_EXT
            )
            for catch_type in catch_types
        }
        LOGGER.info(
            "process data %s - %s at %d month intervals into json files",
            start.strftime(TIMESTAMP_FMT),
            finish.strftime(TIMESTAMP_FMT),
            interval,
        )
        for catch_type, json_file in json_files_stats.items():
            if os.path.exists(json_file) and args.use_cache:
                LOGGER.info("using existing cache file %s", json_file)
            else:
                LOGGER.info("processing %s data", catch_type)
                traps.get_ctt_outputs(
                    start, finish, interval, catch_type, output_file=json_file,
                )

        # create statistics files
        LOGGER.info("creating statistics files")
        for catch_type, json_file in json_files_stats.items():
            LOGGER.debug("creating correlations")
            correlation_lines = traps.get_correlations(
                json_file,
                CATCH_FRACTION_METRIC,
                json_file.replace(JSON_EXT, "_stats.csv"),
            )
            LOGGER.info(
                "\nCorrelations against %s for %s (%d monthly, %s to %s)\n%s\n",
                metric_tidied(CATCH_FRACTION_METRIC),
                catch_type,
                interval,
                args.start,
                args.finish,
                "\n".join(correlation_lines),
            )
            # create seasonality files for catches
            LOGGER.debug("creating seasonailities")
            seasonality_lines = traps.get_seasonality_lines(
                json_file,
                CATCH_COUNT_METRIC,
                args.start,
                args.finish,
                interval,
                json_file.replace(JSON_EXT, "_seasonality.csv"),
                catch_type
            )
            LOGGER.info(
                "\nSeasonality of %s for %s (%d monthly, %s to %s)\n%s\n",
                CATCH_COUNT_METRIC,
                catch_type,
                interval,
                args.start,
                args.finish,
                "\n".join(seasonality_lines),
            )

    finally:
        if initial_wd != base_folder:
            os.chdir(initial_wd)


if __name__ == "__main__":
    main()
