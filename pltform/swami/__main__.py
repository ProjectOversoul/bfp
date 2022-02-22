#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from datetime import datetime
from collections.abc import Iterable
import json
from pprint import pformat

from ..utils import parse_argv
from ..core import cfg
from ..db_core import db
from ..game import Game
from . import Swami, SwamiPick

############
# get_pick #
############

def get_pick(swami_name: str, game_id: int) -> int:
    """Print swami pick for specified game (simple test function)
    """
    swami = Swami.get_by_name(swami_name)
    game = Game.get_by_id(game_id)
    team, _, margin, total = swami.get_pick(game)
    info = game.get_info()
    results = game.get_results()

    pp_params = {'sort_dicts': False}
    print("Game Info:\n", pformat(info._asdict(), **pp_params))
    print(f"\nYour pick: {team} by {margin}")
    print("\nResults:\n", pformat(results._asdict(), **pp_params))

    outcome = ("wrong", "right")
    print(f"\nYou were {outcome[int(team == results.winner)]}!")
    return 0

#############
# load_data #
#############

NO_LOAD = {'default'}

def load_data() -> int:
    """Load (or reload) swami data from config file into database
    """
    nswamis = 0
    swamis = cfg.config('swamis')
    with db.atomic():
        for name, info in swamis.items():
            if name in NO_LOAD:
                print(f"Skipping swami '{name}'")
                continue
            info['name'] = name
            if info.get('swami_params'):
                info['swami_params'] = json.dumps(info['swami_params'])
            print(f"Loading swami '{name}'")
            Swami.create(**info)
            nswamis += 1

    print(f"{nswamis} swamis loaded")
    return 0

##############
# load_picks #
##############

def swami_picks_iter(swami: Swami, season: int) -> dict:
    query = (Game
             .select()
             .where(Game.season == season)
             .iterator())
    now = datetime.now()
    for game in query:
        pick = swami.make_pick(game.get_info())
        swami_pick_data = {'swami':   swami,
                           'game':    game,
                           'pick_ts': now}
        swami_pick_data |= pick._asdict()
        yield swami_pick_data

def load_picks(seasons: Iterable[int], swamis: Iterable[int] = None) -> int:
    query = Swami.select()
    if swamis:
        query = query.where(Swami.name << list(swamis))

    # we do a separate atomic batch insert for each swami and season
    for swami in query:
        for season in seasons:
            picks_data = []
            for pick_data in swami_picks_iter(swami, season):
                picks_data.append(pick_data)
            if picks_data:
                with db.atomic():
                    SwamiPick.insert_many(picks_data).execute()

    return 0

########
# main #
########

def main() -> int:
    """Built-in driver to invoke various utility functions for the module

    Usage: python -m swami <util_func> [<args> ...]

    Functions/usage:
      - get_pick <swami_name> <game_id>
      - load_data
      - load_picks seasons=<seasons> [swamis=<swami>[,...]]
    """
    if len(sys.argv) < 2:
        print(f"Utility function not specified", file=sys.stderr)
        return -1
    elif sys.argv[1] not in globals():
        print(f"Unknown utility function '{sys.argv[1]}'", file=sys.stderr)
        return -1

    util_func = globals()[sys.argv[1]]
    args, kwargs = parse_argv(sys.argv[2:])

    # special parsing for `seasons` arg, and convert to list
    if 'seasons' in kwargs:
        if isinstance(kwargs['seasons'], str):
            if ',' in kwargs['seasons']:
                kwargs['seasons'] = [int(x) for x in kwargs['seasons'].split(',')]
            elif '-' in kwargs['seasons']:
                start, end = kwargs['seasons'].split('-', 1)
                kwargs['seasons'] = range(int(start), int(end) + 1)
            else:
                kwargs['seasons'] = [int(kwargs['seasons'])]
        else:
            kwargs['seasons'] = [kwargs['seasons']]

    if 'swamis' in kwargs:
        # cast to `str` to cover case of numeric swami name
        kwargs['swamis'] = [x for x in str(kwargs['swamis']).split(',')]

    return util_func(*args, **kwargs)

if __name__ == '__main__':
    sys.exit(main())
