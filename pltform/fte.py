#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections.abc import Iterable
from datetime import datetime
from time import sleep

import regex as re
import requests
from bs4 import BeautifulSoup, Tag
from peewee import *

from .utils import parse_argv, replace_tokens
from .core import cfg, DataFile, log, ConfigError, DataError
from .db_core import db
from .team import TEAMS, Team
from .game import PlayoffWeek, Game
from .swami import Swami, SwamiPick

DATA_SRC_KEY = 'data_sources'
FTE_SECT_KEY = 'fte'

data_src = cfg.config(DATA_SRC_KEY)
if not data_src or FTE_SECT_KEY not in data_src:
    raise ConfigError("'{DATA_SRC_KEY}' or '{FTE_SECT_KEY}' not found in config file")
FTE = data_src.get(FTE_SECT_KEY)

# optional in config file (usable defaults here)
HTML_PARSER    = FTE.get('html_parser')    or 'lxml'
HTTP_HEADERS   = FTE.get('http_headers')   or {'User-Agent': 'Mozilla/5.0'}
FETCH_INTERVAL = FTE.get('fetch_interval') or 1.0
SWAMI_NAME     = FTE.get('swami_name')     or 'FiveThirtyEight'

################
# Data Mapping #
################

PLAYOFF_WEEK_MAP = {'Wild-card round':  PlayoffWeek.WC,
                    'Divisional round': PlayoffWeek.DIV,
                    'Conference championships': PlayoffWeek.CONF,
                    'Super Bowl':       PlayoffWeek.SB}

def week_conv(value: str) -> int:
    if m := re.fullmatch(r'Week (\d+)', value):
        return int(m.group(1))
    if week_val := PLAYOFF_WEEK_MAP.get(value):
        return week_val.value
    raise DataError(f"Unknown week value '{value}'")

PICKEM_STR = "PK"

def str_proc(value: str) -> str:
    return value

def int_proc(value: str) -> int:
    return int(value)

def float_proc(value: str) -> float:
    return None if value == '' else float(value)

def spread_proc(value: str) -> float:
    if value == PICKEM_STR:
        return 0.0
    return None if value == '' else float(value)

def pct_proc(value: str) -> int:
    return int(value.split('%')[0])

def team_proc(value: str) -> str:
    if value not in TEAM_NAME:
        raise DataError(f"Unrecognized team name '{value}'")
    return TEAM_NAME[value]

TYPE_PROC = {'str':    str_proc,
             'int':    int_proc,
             'float':  float_proc,
             'spread': spread_proc,
             'pct':    pct_proc,
             'team':   team_proc}

# mapping from FTE team name(s) to `Team` primary key
TEAM_NAME = {}
for code, info in TEAMS.items():
    fte_names = info.get('fte_names')
    if not fte_names:
        raise ConfigError(f"'fte_names' not found for team '{code}'")
    for name in fte_names:
        TEAM_NAME[name] = code

################
# Predict Data #
################

FTE_COMPLETED     = "Completed"

# must be specified in config file
FTE_PREDICT_URL   = FTE['predict_url']
FTE_PREDICT_FILE  = FTE['predict_file']
FTE_PREDICT_STATS = FTE['predict_stats']

def fetch_predict_data(years: Iterable[int]) -> int:
    url_fmt  = FTE_PREDICT_URL
    file_fmt = FTE_PREDICT_FILE

    sess = requests.Session()
    for i, year in enumerate(years):
        if i > 0:
            sleep(FETCH_INTERVAL)  # be nice to website
        url  = replace_tokens(url_fmt, year=str(year))
        req  = sess.get(url, headers=HTTP_HEADERS)
        if not req.ok:
            log.info(f"GET '{url}' returned status code {req.status_code}, skipping...")
            continue
        html = req.text
        log.debug(f"Downloaded {len(html)} bytes from '{url}'")

        file_name = replace_tokens(file_fmt, year=str(year))
        file_path = DataFile(file_name)
        with open(file_path, 'w') as f:
            nbytes = f.write(html)
        log.debug(f"Wrote {nbytes} bytes to '{file_path}'")

    return 0

def predict_data_iter(swami: Swami, year: int, data: list[tuple]) -> dict:
    """Note that there is not enough information to be able to predict total points,
    so we leave that pick field empty.  In the future, the `chance` stat can be used
    (along with `spread`) to determine level of confidence/ranking of picks.
    """
    for i, rec in enumerate(data):
        week      = rec[0]
        home_data = rec[1][1]
        away_data = rec[1][0]
        home_team = Team.get(Team.code == home_data['team'])
        away_team = Team.get(Team.code == away_data['team'])

        try:
            game = Game.get(Game.season == year,
                            Game.week == week,
                            Game.home_team == home_team,
                            Game.away_team == away_team)
        except DoesNotExist:
            # note that teams may be flipped if played at neutral site, so
            # try again, but validate the neutrality aspect
            game = Game.get(Game.season == year,
                            Game.week == week,
                            Game.home_team == away_team,
                            Game.away_team == home_team)
            if not game.neutral_site:
                raise DataError(f"Teams flipped for non-neutral site, game_id {game.id}")
        # note that "pick'em" may be placed against either team--even though
        # that is translated into 0.0, use that team as the favorite
        if away_data['spread'] is not None:
            winner    = away_team
            my_spread = -away_data['spread']
            margin    = my_spread
        else:
            winner    = home_team
            my_spread = home_data['spread']
            margin    = -my_spread
        assert margin >= 0.0

        if game.pt_spread is None:
            ats_winner = None
        else:
            ats_winner = away_team if my_spread > game.pt_spread else home_team
        swami_pick_data = {'swami':      swami,
                           'game':       game,
                           'su_winner':  winner,
                           'ats_winner': ats_winner,
                           'pts_margin': max(round(margin), 1),
                           'total_pts':  0,
                           'pick_ts':    datetime.now()}
        yield swami_pick_data

def parse_predict_data(html: str) -> list[tuple]:
    """Returns the following tuple: (week, (away_data, home_data))
    """
    predict_meta = FTE_PREDICT_STATS

    parsed = []
    soup  = BeautifulSoup(html, HTML_PARSER)

    # build field processor based on predict metadata
    field_proc = {}
    for col_key, col_type in predict_meta.items():
        field_proc[col_key] = TYPE_PROC[col_type]

    def parse_game_table(table: Tag) -> tuple[dict, dict]:
        """Returns tuple of team prediction data: (away_data, home_data)
        """
        team_data = []
        for tr in table('tr'):
            row_data = {}
            for col_key in field_proc:
                value = tr.select(f'td.{col_key}')[0].string
                row_data[col_key] = None if value is None else field_proc[col_key](value.strip())
            team_data.append(row_data)
        if len(team_data) != 2:
            raise DataError(f"Expected two team rows, got {len(team_data)}")
        return tuple(team_data)

    for h3 in soup('h3', class_='h3'):
        # process the week
        week_str = h3.string
        week_num = week_conv(week_str)
        days = h3.next_sibling
        for h4 in days('h4'):
            # process the date
            date_str = h4.string
            date_elems = [x.strip(',.') for x in date_str.split(' ')]
            if len(date_elems) == 3:
                date_elems.append(None)
            if len(date_elems) != 4:
                raise DataError(f"Could not parse date string {date_str}")
            day_of_week, mon, day, year = date_elems
            # NOTE: should be okay to ignore the date elements and just depend on
            # the combination of year, week, and teams to identify the target game
            # for the prediction; but the date information is available if we ever
            # want to do integrity checking, etc.
            games_wrap = h4.next_sibling
            for table in games_wrap('table', class_='game-body'):
                # process the game
                predict_data = parse_game_table(table)
                parsed.append(((week_num, predict_data)))

    return parsed

def load_predict_data(years: Iterable[int]) -> int:
    file_fmt = FTE_PREDICT_FILE

    if db.is_closed():
        db.connect()

    swami = Swami.get_by_name(SWAMI_NAME)

    # note that we do a separate atomic batch insert for each year
    for year in years:
        file_name = replace_tokens(file_fmt, year=str(year))
        file_path = DataFile(file_name)
        try:
            with open(file_path, 'r') as f:
                html = f.read()
        except FileNotFoundError:
            log.info(f"File {file_path} not found, skipping...")
            continue
        log.debug(f"Read {len(html)} bytes from '{file_path}'")
        parsed = parse_predict_data(html)
        picks_data = []
        for predict_data in predict_data_iter(swami, year, parsed):
            picks_data.append(predict_data)
        if picks_data:
            with db.atomic():
                SwamiPick.insert_many(picks_data).execute()

    return 0

########
# Main #
########

def main() -> int:
    """Built-in driver to invoke various utility functions for the module

    Usage: fte.py <util_func> [<args> ...]

    Functions/usage:
      - fetch_predict_data years=<years>
      - load_predict_data years=<years>

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
