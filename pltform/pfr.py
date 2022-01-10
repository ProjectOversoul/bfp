#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections.abc import Iterable
from datetime import datetime, date, time
from time import sleep
import re

import regex as re
import requests
from bs4 import BeautifulSoup, Tag
from peewee import *

from .utils import parse_argv
from .core import cfg, DataFile, log, ConfigError, DataError
from .team import TEAMS
from .game import Game

DATA_SRC_KEY = 'data_sources'
PFR_SECT_KEY = 'pfr'
data_src = cfg.config(DATA_SRC_KEY)
if not data_src or PFR_SECT_KEY not in data_src:
    raise ConfigError("'{DATA_SRC_KEY}' or '{PFR_SECT_KEY}' not found in config file")
PFR = data_src.get(PFR_SECT_KEY)

#############
# Team Data #
#############

# mapping from PFR team code to `Team` primary key
TEAM_CODE = {}
for code, info in TEAMS.items():
    pfr_code = info.get('pfr_code')
    if not pfr_code:
        raise ConfigError(f"'pfr_code' not found for team '{code}'")
    TEAM_CODE[pfr_code] = code

#############
# Game Data #
#############

GAMES_URL_KEY   = 'games_url'
GAMES_FILE_KEY  = 'games_file'
GAMES_STATS_KEY = 'games_stats'
HTML_PARSER     = 'lxml'
HTTP_HEADERS    = {'User-Agent': 'Mozilla/5.0'}
SLEEP_TIME      = 1.0

DATE_FMT        = '%Y-%m-%d'
TIME_FMT        = '%I:%M%p'
TEAM_HREF_PFX   = ['', 'teams']

def str_proc(value: str) -> str:
    return value

def int_proc(value: str) -> int:
    return int(value)

def date_proc(value: str) -> date:
    return datetime.strptime(value, DATE_FMT).date()

def time_proc(value: str) -> time:
    return datetime.strptime(value, TIME_FMT).time()

def team_proc(value: str) -> str:
    # input string (href) has format: "/teams/atl/2021.htm"
    elems = value.split('/')
    if len(elems) != 4 or elems[:2] != TEAM_HREF_PFX:
        raise DataError(f"Unexpected format for href '{value}'")
    return TEAM_CODE[elems[2]]

TYPE_PROC = {'str':  str_proc,
             'int':  int_proc,
             'date': date_proc,
             'time': time_proc,
             'team': team_proc}

def replace_tokens(fmt: str, **kwargs) -> str:
    new_str = fmt
    tokens = re.findall(r'(\<[\p{Lu}\d_]+\>)', fmt)
    for token in tokens:
        token_var = token[1:-1].lower()
        value = kwargs.get(token_var)
        if not value:
            raise RuntimeError(f"Token '{token_var}' not found in {kwargs}")
        new_str = new_str.replace(token, value)
    return new_str

def get_game_data(years: Iterable[int]) -> None:
    url_fmt = PFR[GAMES_URL_KEY]
    file_fmt = PFR[GAMES_FILE_KEY]

    sess = requests.Session()
    for year in years:
        url  = replace_tokens(url_fmt, year=str(year))
        req  = sess.get(url, headers=HTTP_HEADERS)
        html = req.text
        log.debug(f"Downloaded {len(html)} bytes from '{url}'")

        file_path = DataFile(replace_tokens(file_fmt, year=str(year)))
        with open(file_path, 'w') as f:
            nbytes = f.write(html)
        log.debug(f"Wrote {nbytes} bytes to '{file_path}'")
        sleep(SLEEP_TIME)

def as_game_dict(data: dict) -> dict:
    """
    season       : int
    week         : int  # ordinal within season, or special `Week` value
    day          : int  # day of week 0-6 (Mon-Sun)
    datetime     : datetime
    home_team    : team_code
    away_team    : team_code
    boxscore_url : str

    winner       : team_code  # home team, if tie
    loser        : team_code  # away team, if tie
    tie          : bool
    home_pts     : int
    home_yds     : int
    home_tos     : int
    away_pts     : int
    away_yds     : int
    away_tos     : int
    """
    pass

def store_game_data(years: Iterable[int]) -> None:
    file_fmt = PFR[GAMES_FILE_KEY]

    for year in years:
        file_path = DataFile(replace_tokens(file_fmt, year=str(year)))
        with open(file_path, 'r') as f:
            html = f.read()
        log.debug(f"Read {len(html)} bytes from '{file_path}'")
        parsed = parse_game_data(html)

def parse_game_data(html: str) -> list[dict]:
    games_meta = PFR[GAMES_STATS_KEY]

    parsed = []
    soup  = BeautifulSoup(html, HTML_PARSER)
    table = soup.find('table')

    # do integrity check on games metadata, build field processor
    field_proc = {}
    header = table.find('thead')
    for col in header.find_all('th'):
        col_key = col['data-stat']
        if col_key not in games_meta:
            raise DataError(f"Stats type '{col_key}' not in `games_stats`")
        col_type = games_meta[col_key]
        field_proc[col_key] = TYPE_PROC[col_type]

    body = table.find('tbody')
    for i, row in enumerate(body.find_all('tr')):
        if (tr_class := row.get('class')) and 'thead' in tr_class:
            # skip periodic repeat of table header
            continue

        row_data = {}
        for j, col in enumerate(row.find_all(['th', 'td'])):
            col_key = col['data-stat']
            # use href under `a` tag, if it exists (e.g. for teams)
            if anchor := col.find('a') :
                value = anchor['href']
            else:
                value = col.string
            if value is None:
                # this is a special formatting row, skip it
                break
            row_data[col_key] = field_proc[col_key](value)
        if j == 0:
            # broke from inner loop (no data in row)
            continue
        parsed.append(row_data)

    return parsed
    
########
# Main #
########

def main() -> int:
    """Built-in driver to invoke various utility functions for the module

    Usage: pfr.py <func_name> [<args> ...]

    Functions/usage:
      - get_game_data years=<years>
      - store_game_data years=<years>

    where <years> can be:
      - single year    (e.g. '2021')
      - list of years  (e.g. '2018,2019,2020,2021')
      - range of years (e.g. '2018-2021')
    """
    if len(sys.argv) < 2:
        print(f"Utility function not specified", file=sys.stderr)
        return -1
    elif sys.argv[1] not in globals():
        print(f"Unknown utility function '{sys.argv[1]}'", file=sys.stderr)
        return -1

    util_func = globals()[sys.argv[1]]
    args, kwargs = parse_argv(sys.argv[2:])

    # special parsing for `years` arg, and convert to list
    if 'years' in kwargs:
        if isinstance(kwargs['years'], str):
            if ',' in kwargs['years']:
                kwargs['years'] = [int(x) for x in kwargs['years'].split(',')]
            elif '-' in kwargs['years']:
                start, end = kwargs['years'].split('-', 1)
                kwargs['years'] = range(int(start), int(end) + 1)
            else:
                kwargs['years'] = [int(kwargs['years'])]
        else:
            kwargs['years'] = [kwargs['years']]

    return util_func(*args, **kwargs)

if __name__ == '__main__':
    sys.exit(main())
