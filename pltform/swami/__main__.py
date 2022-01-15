#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from pprint import pformat

from ..utils import parse_argv
from ..core import cfg
from ..db_core import db
from ..game import Game
from . import Swami

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
            Swami.my_create(**info)
            nswamis += 1

    print(f"{nswamis} swamis loaded")
    return 0

############
# get_pick #
############

def get_pick(swami_name: str, game_id: int) -> int:
    """Print swami pick for specified game
    """
    swami = Swami.get_by_name(swami_name)
    game = Game.get_by_id(game_id)
    team, _, margin, total = swami.get_pick(game.get_info())
    info = game.get_info()
    results = game.get_results()

    pp_params = {'sort_dicts': False}
    print("Game Info:\n", pformat(info._asdict(), **pp_params))
    print(f"\nYour pick: {team} by {margin}")
    print("\nResults:\n", pformat(results._asdict(), **pp_params))

    outcome = ("wrong", "right")
    print(f"\nYou were {outcome[int(team == results.winner)]}!")
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
    """
    if len(sys.argv) < 2:
        print(f"Utility function not specified", file=sys.stderr)
        return -1
    elif sys.argv[1] not in globals():
        print(f"Unknown utility function '{sys.argv[1]}'", file=sys.stderr)
        return -1

    util_func = globals()[sys.argv[1]]
    args, kwargs = parse_argv(sys.argv[2:])

    return util_func(*args, **kwargs)

if __name__ == '__main__':
    sys.exit(main())
