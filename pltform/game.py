#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from typing import Optional, NamedTuple
from datetime import datetime
from enum import Enum

from peewee import *

from .db_core import BaseModel
from .team import Team

################
# Week/WeekDay #
################

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

PLAYOFF_WEEKS = (w.value for w in Week)

PLAYOFF_WEEK_STR = {100: 'WildCard',
                    200: 'Division',
                    300: 'ConfChamp',
                    400: 'SuperBowl'}

def WeekStr(week: int) -> str:
    if week >= 100:
        return PLAYOFF_WEEK_STR[week]
    return f"Week {week}"

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

########
# Pick #
########

class Pick(NamedTuple):
    """Pick for an individual game, whether based on external data or computation
    from an internal algorithm
    """
    su_winner:  Team
    ats_winner: Team | None  # only if `pt_spread` is available
    pts_margin: int          # must be greater than 0
    total_pts:  int

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
    pt_spread:  Optional[float]  # "pick" is represented by 0.0
    over_under: Optional[float]

###############
# GameResults #
###############

class GameResults(NamedTuple):
    winner:         Team
    loser:          Team
    is_tie:         bool
    winner_pts:     int
    loser_pts:      int
    pts_margin:     int
    total_pts:      int
    home_vs_spread: Optional[float]
    away_vs_spread: Optional[float]
    vs_over_under:  Optional[float]

########
# Game #
########

PICK_STR = 'pick'  # meaning "pick'em", not related to `Pick` class

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
    pt_spread    = FloatField(null=True)  # negative - home favorite, 0 - pick
    over_under   = FloatField(null=True)

    # result/outcome info
    winner       = ForeignKeyField(Team, column_name='winner',
                                   backref='games_won', null=True)   # home team, if tie
    loser        = ForeignKeyField(Team, column_name='loser',
                                   backref='games_lost', null=True)  # away team, if tie
    is_tie       = BooleanField(null=True)
    home_pts     = IntegerField(null=True)
    home_yds     = IntegerField(null=True)
    home_tos     = IntegerField(null=True)
    away_pts     = IntegerField(null=True)
    away_yds     = IntegerField(null=True)
    away_tos     = IntegerField(null=True)

    @property
    def matchup(self) -> str:
        return f"{self.away_team} vs {self.home_team}"

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

    @property
    def ats_winner(self) -> ForeignKeyField | None:
        if self.pt_spread is None or self.home_vs_spread == 0.0:
            return None
        return self.home_team if self.home_vs_spread > 0.0 else self.away_team

    @property
    def ats_loser(self) -> ForeignKeyField | None:
        if self.pt_spread is None or self.home_vs_spread == 0.0:
            return None
        return self.home_team if self.home_vs_spread < 0.0 else self.away_team

    @property
    def home_vs_spread(self) -> float | None:
        if self.pt_spread is None:
            return None
        return self.home_pts + self.pt_spread - self.away_pts

    @property
    def away_vs_spread(self) -> float | None:
        if self.pt_spread is None:
            return None
        return -self.home_vs_spread

    @property
    def vs_over_under(self) -> float | None:
        if self.over_under is None:
            return None
        return self.winner_pts + self.loser_pts - self.over_under

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
                               self.pt_spread,
                               self.over_under))

    def get_results(self) -> GameResults:
        """Return results as a NamedTuple (some computation involved)
        """
        return GameResults._make((self.winner,
                                  self.loser,
                                  self.home_pts == self.away_pts,
                                  self.winner_pts,
                                  self.loser_pts,
                                  self.winner_pts - self.loser_pts,
                                  self.winner_pts + self.loser_pts,
                                  self.home_vs_spread,
                                  self.away_vs_spread,
                                  self.vs_over_under))

###########
# GameCtx #
###########

"""This is a "conceptual" abstract base class with minimum/common game context
variables needed to implement certain functions that can operate on either
`Game` or `GameInfo` instances.  We can't actually implement this is a more
robust fashion, since `NamedTuple` doesn't support multiple inheritence.

The required context variables are as follows:
  game_id:    int | IntegerField
  season:     int | IntegerField
  week:       int | IntegerField
  datetime:   datetime
  home_team:  Team
  away_team:  Team
"""
GameCtx = GameInfo | Game

########
# Main #
########

def main() -> int:
    pass

if __name__ == '__main__':
    sys.exit(main())
