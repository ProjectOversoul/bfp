#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from typing import NamedTuple

from peewee import *

from .utils import parse_argv
from .core import cfg, ConfigError
from .db_core import db, BaseModel

#################
# Team metadata #
#################

TEAMS_KEY = 'teams'

TEAMS = cfg.config(TEAMS_KEY)
if not TEAMS:
    raise ConfigError(f"'{TEAMS_KEY}' not found in config file")

########
# Team #
########

class Team(BaseModel):
    """Represents a currently active team; note that data for prior incarnations
    of teams (e.g. Decatur Staleys or Oakland Raiders) are incorporated into the
    descendent specified by https://www.pro-football-reference.com/teams (whether
    or not one agrees, cf. Browns->Ravens)
    """
    code      = TextField(primary_key=True)
    name      = TextField(unique=True)
    full_name = TextField()
    conf      = TextField()
    div       = TextField()
    timezone  = TextField()

#############
# load_data #
#############

def load_data() -> int:
    """Load teams data into the database.  The base data is specified in the config
    file for the project.
    """
    teams_data = []
    for code, info in TEAMS.items():
        team_data = {'code'      : code,
                     'name'      : info['name'],
                     'full_name' : info['full_name'],
                     'conf'      : info['conf'],
                     'div'       : info['div'],
                     'timezone'  : info['timezone']}
        teams_data.append(team_data)

    if db.is_closed():
        db.connect()
    with db.atomic():
        # TODO: support a "reload" mode, where a unique key conflict results in an update
        # of non-key fields!!!
        Team.insert_many(teams_data).execute()

    return 0

########
# Main #
########

def main() -> int:
    """Built-in driver to invoke various utility functions for the module

    Usage: team.py <util_func> [<args> ...]

    Functions/usage:
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
