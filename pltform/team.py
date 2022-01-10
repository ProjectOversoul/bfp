#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from peewee import *

from .core import cfg, ConfigError
from .base_model import BaseModel

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
    name      = TextField()
    full_name = TextField()
    conf      = TextField()
    div       = TextField()
    pfr_code  = TextField()
    timezone  = TextField(null=True)

########
# Main #
########

def main() -> int:
    pass

if __name__ == '__main__':
    sys.exit(main())
