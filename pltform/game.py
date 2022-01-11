#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from typing import NamedTuple
from datetime import datetime
from enum import Enum

from peewee import *

from .core import DataError
from .db_core import BaseModel
from .team import Team

########
# Week #
########

# values less than 100 represent the week number within the
# season; playoff games have special values as specified in
# the `Week` enum
Weak = int

# special values
class Week(Enum):
    WC   = 100
    DIV  = 200
    CONF = 300
    SB   = 400

SPC_WEEK_MAP = {'WildCard':  Week.WC,
                'Division':  Week.DIV,
                'ConfChamp': Week.CONF,
                'SuperBowl': Week.SB}

# values consistent with `datetime.weekday()`
class WeekDay(Enum):
    MON = 0
    TUE = 1
    WED = 2
    THU = 3
    FRI = 4
    SAT = 5
    SUN = 6

WEEKDAY_MAP = {'Mon': WeekDay.MON,
               'Tue': WeekDay.TUE,
               'Wed': WeekDay.WED,
               'Thu': WeekDay.THU,
               'Fri': WeekDay.FRI,
               'Sat': WeekDay.SAT,
               'Sun': WeekDay.SUN}

############
# GameInfo #
############

class GameInfo(NamedTuple):
    game_id:    int
    season:     int    # year of season start
    week:       int    # ordinal within season, or special `Week` value
    day:        WeekDay
    datetime:   datetime
    home_team:  Team
    away_team:  Team
    pt_spread:  float  # "pick" is represented by 0.0
    over_under: int

########
# Game #
########

PICK_STR = "pick"

class Game(BaseModel):
    """Represents a single game played or scheduled (`datetime` is the future and
    `winner`, `loser`, etc. fields are null)
    """
    # context/schedule info
    game_id      = AutoField()
    season       = IntegerField()  # year of season start
    week         = IntegerField()  # ordinal within season, or special `Week` value
    day          = IntegerField()  # day of week 0-6 (Mon-Sun)
    datetime     = DateTimeField()
    home_team    = ForeignKeyField(Team, column_name='home_team', backref='home_games')
    away_team    = ForeignKeyField(Team, column_name='away_team', backref='away_games')
    boxscore_url = TextField()

    # enrichment info
    pt_spread    = TextField(null=True)  # e.g. "-7", +3.5", or "pick"
    over_under   = IntegerField(null=True)

    # result/outcome info
    winner       = ForeignKeyField(Team, column_name='winner',
                                   backref='games_won', null=True)   # home team, if tie
    loser        = ForeignKeyField(Team, column_name='loser',
                                   backref='games_lost', null=True)  # away team, if tie
    tie          = BooleanField(null=True)
    home_pts     = IntegerField(null=True)
    home_yds     = IntegerField(null=True)
    home_tos     = IntegerField(null=True)
    away_pts     = IntegerField(null=True)
    away_yds     = IntegerField(null=True)
    away_tos     = IntegerField(null=True)

    @property
    def winner_pts(self) -> IntegerField:
        return self.home_pts if self.winner == self.home_team else self.away_pts

    @property
    def winner_yds(self) -> IntegerField:
        return self.home_yds if self.winner == self.home_team else self.away_yds

    @property
    def winner_tos(self) -> IntegerField:
        return self.home_tos if self.winner == self.home_team else self.away_tos

    @property
    def loser_pts(self) -> IntegerField:
        return self.home_pts if self.loser == self.home_team else self.away_pts

    @property
    def loser_yds(self) -> IntegerField:
        return self.home_yds if self.loser == self.home_team else self.away_yds

    @property
    def loser_tos(self) -> IntegerField:
        return self.home_tos if self.loser == self.home_team else self.away_tos

    def pt_spread_num(self) -> float:
        """Return point spread as a numeric value with 0.0 representing "pick".

        Note, this is specified as a method rather than a property because it
        is just an alternate representation of a variable and not a new piece
        of information.
        """
        if str(self.pt_spread).isnumeric():
            return float(str(self.pt_spread))
        elif self.pt_spread == PICK_STR:
            return 0.0
        raise DataError(f"Bad value for `pt_spread`: {self.pt_spread}")

    def get_info(self) -> GameInfo:
        """Return just the context/schedule fields as a NamedTuple (e.g. so swamis won't
        be tempted to use completed game data in computing picks--as if Python actually
        had security preventing such shananigans, lol)
        """
        return GameInfo._make((self.game_id,
                               self.season,
                               self.week,
                               WeekDay(self.day),
                               self.datetime,
                               self.home_team,
                               self.away_team,
                               self.pt_spread_num(),
                               self.over_under))

########
# Main #
########

def main() -> int:
    pass

if __name__ == '__main__':
    sys.exit(main())
