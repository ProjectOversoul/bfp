#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections.abc import Iterable
from datetime import datetime, date, time
from time import sleep

import requests
from bs4 import BeautifulSoup, Tag
from peewee import *

from .utils import parse_argv, replace_tokens
from .core import cfg, DataFile, log, ConfigError, DataError
from .db_core import db
from .team import TEAMS
from .game import PlayoffWeek, WeekDay, Game

DATA_SRC_KEY = 'data_sources'
PFR_SECT_KEY = 'pfr'

data_src = cfg.config(DATA_SRC_KEY)
if not data_src or PFR_SECT_KEY not in data_src:
    raise ConfigError("'{DATA_SRC_KEY}' or '{PFR_SECT_KEY}' not found in config file")
PFR = data_src.get(PFR_SECT_KEY)

# optional in config file (usable defaults here)
HTML_PARSER    = PFR.get('html_parser')    or 'lxml'
HTTP_HEADERS   = PFR.get('http_headers')   or {'User-Agent': 'Mozilla/5.0'}
FETCH_INTERVAL = PFR.get('fetch_interval') or 1.0

################
# Data Mapping #
################

PLAYOFF_WEEK_MAP = {'WildCard':  PlayoffWeek.WC,
                    'Division':  PlayoffWeek.DIV,
                    'ConfChamp': PlayoffWeek.CONF,
                    'SuperBowl': PlayoffWeek.SB}

def week_conv(value: str) -> int:
    if value.isnumeric():
        return int(value)
    if week_val := PLAYOFF_WEEK_MAP.get(value):
        return week_val.value
    raise DataError(f"Unknown week value '{value}'")

WEEKDAY_MAP = {'Mon': WeekDay.MON,
               'Tue': WeekDay.TUE,
               'Wed': WeekDay.WED,
               'Thu': WeekDay.THU,
               'Fri': WeekDay.FRI,
               'Sat': WeekDay.SAT,
               'Sun': WeekDay.SUN}

def weekday_conv(value: str) -> int:
    if weekday_val := WEEKDAY_MAP.get(value):
        return weekday_val.value
    raise DataError(f"Unknown weekday value '{value}'")

DATE_FMT       = '%Y-%m-%d'
TIME_FMT       = '%I:%M%p'
TEAM_HREF_PFX  = ['', 'teams']

def str_proc(value: str) -> str:
    return value

def int_proc(value: str) -> int:
    return int(value)

def float_proc(value: str) -> float:
    return float(value)

def date_proc(value: str) -> date:
    return datetime.strptime(value, DATE_FMT).date()

def time_proc(value: str) -> time:
    return datetime.strptime(value, TIME_FMT).time()

def team_proc(value: str) -> str:
    """Convert team URL to `Team` primary key

    :param value: PFR team URL (e.g. "/teams/atl/2021.htm")
    :return: `Team` code (primary key)
    """
    elems = value.split('/')
    if len(elems) != 4 or elems[:2] != TEAM_HREF_PFX:
        raise DataError(f"Unexpected format for href '{value}'")
    return TEAM_CODE[elems[2]]

TYPE_PROC = {'str':   str_proc,
             'int':   int_proc,
             'float': float_proc,
             'date':  date_proc,
             'time':  time_proc,
             'team':  team_proc}

# mapping from PFR team code to `Team` primary key
TEAM_NO_MAP = {'NONE'}
TEAM_CODE = {}
for code, info in TEAMS.items():
    if code in TEAM_NO_MAP:
        continue
    pfr_code = info.get('pfr_code')
    if not pfr_code:
        raise ConfigError(f"'pfr_code' not found for team '{code}'")
    TEAM_CODE[pfr_code] = code

#############
# Game Data #
#############

# must be specified in config file
PFR_GAMES_URL   = PFR['games_url']
PFR_GAMES_FILE  = PFR['games_file']
PFR_GAMES_STATS = PFR['games_stats']

def fetch_game_data(years: Iterable[int]) -> int:
    url_fmt  = PFR_GAMES_URL
    file_fmt = PFR_GAMES_FILE

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

        file_path = DataFile(replace_tokens(file_fmt, year=str(year)))
        with open(file_path, 'w') as f:
            nbytes = f.write(html)
        log.debug(f"Wrote {nbytes} bytes to '{file_path}'")

    return 0

def parse_game_data(html: str) -> list[dict]:
    games_meta = PFR_GAMES_STATS

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
        # skip periodic repeat of table header
        if (tr_class := row.get('class')) and 'thead' in tr_class:
            continue

        row_data = {}
        for j, col in enumerate(row.find_all(['th', 'td'])):
            col_key = col['data-stat']
            # use href under `a` tag, if it exists (e.g. for teams)
            if anchor := col.find('a') :
                value = anchor['href']
            else:
                value = col.string
            # if this is a special formatting row, bail (and skip row below)
            if j == 0 and value is None:
                break
            row_data[col_key] = None if value is None else field_proc[col_key](value)
        # broke from inner loop (no data in row), skip it
        if j == 0:
            continue
        parsed.append(row_data)

    return parsed

def game_data_iter(year: int, data: list[dict]) -> dict:
    """Iterator for games data, yields a dict suitable for feeding into `Game`
    """
    for i, rec in enumerate(data):
        if not rec['game_location'] or rec['game_location'] == 'N':
            home_team = rec['winner']
            away_team = rec['loser']
            is_tie    = rec['pts_win'] == rec['pts_lose']
            home_pts  = rec['pts_win']
            home_yds  = rec['yards_win']
            home_tos  = rec['to_win']
            away_pts  = rec['pts_lose']
            away_yds  = rec['yards_lose']
            away_tos  = rec['to_lose']
        else:
            if rec['game_location'] != '@':
                raise RuntimeError(f"Unexpected value for `game_location`: "
                                   f"'{rec['game_location']}' (rec {i})")
            away_team = rec['winner']
            home_team = rec['loser']
            is_tie    = False
            away_pts  = rec['pts_win']
            away_yds  = rec['yards_win']
            away_tos  = rec['to_win']
            home_pts  = rec['pts_lose']
            home_yds  = rec['yards_lose']
            home_tos  = rec['to_lose']
        played = home_pts is not None

        game_data = {'season'       : year,
                     'week'         : week_conv(rec['week_num']),
                     'day'          : weekday_conv(rec['game_day_of_week']),
                     'datetime'     : datetime.combine(rec['game_date'], rec['gametime']),
                     'home_team'    : home_team,
                     'away_team'    : away_team,
                     'neutral_site' : rec['game_location'] == 'N',
                     'boxscore_url' : rec['boxscore_word'],
                     'winner'       : rec['winner'] if played else None,  # home team, if tie
                     'loser'        : rec['loser']  if played else None,  # away team, if tie
                     'is_tie'       : is_tie        if played else None,
                     'home_pts'     : home_pts,
                     'home_yds'     : home_yds,
                     'home_tos'     : home_tos,
                     'away_pts'     : away_pts,
                     'away_yds'     : away_yds,
                     'away_tos'     : away_tos}
        yield game_data

def load_game_data(years: Iterable[int]) -> int:
    file_fmt = PFR_GAMES_FILE

    if db.is_closed():
        db.connect()

    # note that we do a separate atomic batch insert for each year
    for year in years:
        file_path = DataFile(replace_tokens(file_fmt, year=str(year)))
        try:
            with open(file_path, 'r') as f:
                html = f.read()
        except FileNotFoundError:
            log.info(f"File {file_path} not found, skipping...")
            continue
        log.debug(f"Read {len(html)} bytes from '{file_path}'")
        parsed = parse_game_data(html)
        games_data = []
        for game_data in game_data_iter(year, parsed):
            games_data.append(game_data)
        with db.atomic():
            Game.replace_many(games_data).execute()

    return 0

###################
# Vegas Line Data #
###################

# must be specified in config file
PFR_LINES_URL   = PFR['lines_url']
PFR_LINES_FILE  = PFR['lines_file']
PFR_LINES_STATS = PFR['lines_stats']

def fetch_line_data(years: Iterable[int]) -> int:
    url_fmt  = PFR_LINES_URL
    file_fmt = PFR_LINES_FILE

    sess = requests.Session()
    for i, year in enumerate(years):
        for j, team_code in enumerate(TEAM_CODE):
            if i > 0 or j > 0:
                sleep(FETCH_INTERVAL)  # be nice to website
            url  = replace_tokens(url_fmt, year=str(year), team_code=team_code)
            req  = sess.get(url, headers=HTTP_HEADERS)
            if not req.ok:
                log.info(f"GET '{url}' returned status code {req.status_code}, skipping...")
                continue
            html = req.text
            log.debug(f"Downloaded {len(html)} bytes from '{url}'")

            file_name = replace_tokens(file_fmt, year=str(year), team_code=team_code)
            file_path = DataFile(file_name)
            with open(file_path, 'w') as f:
                nbytes = f.write(html)
            log.debug(f"Wrote {nbytes} bytes to '{file_path}'")

    return 0

def line_data_iter(team_code: str, data: list[dict]) -> Game:
    """Iterator for Vegas line data, yields a `Game` object with `pt_spread` and
    `over_under` fields updated (based on parsed `data`), suitable for inclusion
    in `Game.bulk_update()` call

    :param team_code: PFR team code associated with `data`
    :param data: parsed data from PFR "Vegas Lines" table for `team_code`
    :return: `Game` with updated line-related fields
    """
    cur_team = TEAM_CODE[team_code]

    for i, rec in enumerate(data):
        opp_team     = rec['opp']
        vegas_line   = rec['vegas_line']
        over_under   = rec['over_under']
        boxscore_url = rec['game_result']

        game = Game.get(Game.boxscore_url == boxscore_url)
        is_home = game.home_team.code == cur_team
        if is_home:
            if game.away_team.code != opp_team:
                raise DataError(f"Away team conflict ({opp_team}) for game_id {game.id}")
        else:
            if game.away_team.code != cur_team:
                raise DataError(f"Away team conflict ({cur_team}) for game_id {game.id}")
            if game.home_team.code != opp_team:
                raise DataError(f"Home team conflict ({opp_team}) for game_id {game.id}")

        pt_spread = vegas_line if is_home else -vegas_line
        if game.pt_spread is None:
            # assume these are always updated together
            game.pt_spread = pt_spread
            game.over_under = over_under
            yield game
        else:
            if game.pt_spread != pt_spread or game.over_under != over_under:
                raise DataError(f"Vegas line conflict ({pt_spread}, {over_under}) "
                                f"for game_id {game.id}")

def parse_line_data(html: str) -> list[dict]:
    lines_meta = PFR_LINES_STATS

    parsed = []
    soup  = BeautifulSoup(html, HTML_PARSER)
    table = soup.find('table')

    # do integrity check on lines metadata, build field processor
    field_proc = {}
    header = table.find('thead')
    for col in header.find_all('th'):
        col_key = col['data-stat']
        if col_key not in lines_meta:
            raise DataError(f"Stats type '{col_key}' not in `lines_stats`")
        col_type = lines_meta[col_key]
        field_proc[col_key] = TYPE_PROC[col_type]

    body = table.find('tbody')
    for i, row in enumerate(body.find_all('tr')):
        row_data = {}
        for j, col in enumerate(row.find_all(['th', 'td'])):
            col_key = col['data-stat']
            # use href under `a` tag, if it exists (e.g. for teams)
            if anchor := col.find('a') :
                value = anchor['href']
            else:
                value = col.string
            row_data[col_key] = None if value is None else field_proc[col_key](value)
        parsed.append(row_data)

    return parsed

def load_line_data(years: Iterable[int]) -> int:
    file_fmt = PFR_LINES_FILE

    if db.is_closed():
        db.connect()

    # note that we do a separate atomic batch update for each team's games in a given
    # year, noting that games already updated (via opposing team's update pass) are
    # skipped, after validating consistency
    for year in years:
        for team_code in TEAM_CODE:
            file_name = replace_tokens(file_fmt, year=str(year), team_code=team_code)
            file_path = DataFile(file_name)
            try:
                with open(file_path, 'r') as f:
                    html = f.read()
            except FileNotFoundError:
                log.info(f"File {file_path} not found, skipping...")
                continue
            log.debug(f"Read {len(html)} bytes from '{file_path}'")
            parsed = parse_line_data(html)
            upd_games = []
            for upd_game in line_data_iter(team_code, parsed):
                upd_games.append(upd_game)
            if upd_games:
                with db.atomic():
                    Game.bulk_update(upd_games, fields=[Game.pt_spread, Game.over_under])

    return 0

########
# Main #
########

def main() -> int:
    """Built-in driver to invoke various utility functions for the module

    Usage: pfr.py <util_func> [<args> ...]

    Functions/usage:
      - fetch_game_data years=<years>
      - load_game_data years=<years>
      - fetch_line_data years=<years>
      - load_line_data years=<years>

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
