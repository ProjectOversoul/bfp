# -*- coding: utf-8 -*-

from typing import ClassVar, NamedTuple
from datetime import datetime
from enum import Enum

from peewee import ModelSelect, query_to_string

from .core import LogicError, ImplementationError
from .team import Team
from .game import Game, GameInfo

##############
# FilterType #
##############

class FilterType(Enum):
    """This is used to sort filters by the order in which they should be
    logically applied to the underlying query (even if the ORM does not
    completely insist on it)
    """
    SELECT   = 1
    JOIN     = 2
    WHERE    = 3
    GROUP_BY = 4
    HAVING   = 5
    ORDER_BY = 6
    LIMIT    = 7

###########
# Filters #
###########

class AnlyFilter:
    """Abstract base class for analysis filters, should not be instantiated
    directly.

    TODO:
      - represent dependencies (or implicity invoke)
      - represent imcompatibilities (and how to signal)
    """
    type: ClassVar[FilterType]

    def __init__(self, *args, **kwargs):
        """Note that subclasses should not call the super class constructor.
        """
        raise ImplementationError("Should not be called by subclass __init__")

    def apply(self, query: ModelSelect) -> ModelSelect:
        raise ImplementationError("Must be implemented by subclass")

class AnlyFilterVenue(AnlyFilter):
    """Filter specifying home vs. away games to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class AnlyFilterTeam(AnlyFilter):
    """Filter specifying opposing team to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class AnlyFilterConf(AnlyFilter):
    """Filter specifying opponent team conference to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class AnlyFilterDiv(AnlyFilter):
    """Filter specifying opponent team division to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class AnlyFilterGames(AnlyFilter):
    """Filter specifying number of qualitfying games to evaluate
    """
    type = FilterType.LIMIT

    games: int

    def __init__(self, games: int):
        self.games = games

    def apply(self, query: ModelSelect) -> ModelSelect:
        return query.limit(self.games)

class AnlyFilterSeasons(AnlyFilter):
    """Filter specifying number of seasons to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class AnlyFilterWeeks(AnlyFilter):
    """Filter specifying which weeks within the season to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class AnlyFilterRecord(AnlyFilter):
    """Filter specifying the current/opponent team point-in-time season
    records for games to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class AnlyFilterSpread(AnlyFilter):
    """Filter specifying the spread (relative to current team) for games
    to evaluate
    """
    def __init__(self, *args, **kwargs):
        pass

class _AnlyFilterTimeframe(AnlyFilter):
    """Filter specifying the timeframe for the analysis (games considered must be
    earlier than the reference datetime), applied implicitly by the framework.
    """
    type = FilterType.WHERE

    timeframe: datetime

    def __init__(self, timeframe: datetime):
        self.timeframe = timeframe

    def apply(self, query: ModelSelect) -> ModelSelect:
        return query.where((Game.datetime < str(self.timeframe)))

class _AnlyFilterPriTeam(AnlyFilter):
    """Filter specifying the primary team for the analysis, applied implicitly
    by the framework.
    """
    type = FilterType.WHERE

    team: Team

    def __init__(self, team: Team):
        self.team = team

    def apply(self, query: ModelSelect) -> ModelSelect:
        return query.where((Game.home_team == str(self.team)) |
                           (Game.away_team == str(self.team)))

class _AnlyFilterRevChron(AnlyFilter):
    """Filter specifying reverse chronological order for results so that the
    LIMIT filters work right, applied implicitly by the framework.
    """
    type = FilterType.ORDER_BY

    def __init__(self, *args, **kwargs):
        pass

    def apply(self, query: ModelSelect) -> ModelSelect:
        return query.order_by(Game.datetime.desc())

#########
# Stats #
#########

class AnlyStats(NamedTuple):
    games:       list[Game]
    wins:        list[Game]
    losses:      list[Game]
    ties:        list[Game]
    ats_wins:    list[Game]  # wins against the spread (beat or cover)
    pts_for:     int
    pts_against: int
    yds_for:     int
    yds_against: int
    tos_for:     int
    tos_against: int

    @property
    def win_pct(self) -> float:
        return len(self.wins) / len(self.games) * 100.0

    @property
    def loss_pct(self) -> float:
        return len(self.losses) / len(self.games) * 100.0

    @property
    def ats_pct(self) -> float:
        return len(self.ats_wins) / len(self.games) * 100.0

    @property
    def pts_margin(self) -> float:
        """Average points margin
        """
        return (self.pts_for - self.pts_against) / len(self.games)

############
# Analysis #
############

class Analysis:
    """Analysis object with stats for specified team and evaluation filters
    """
    game_info: GameInfo
    team:      Team
    filters:   list[AnlyFilter]
    frozen:    bool
    _stats:    AnlyStats = None

    def __init__(self, game_info: GameInfo, team: Team, filters: list[AnlyFilter] = None):
        """REVISIT: the args for this constructor are kind of messy, but currently need
        `game_info` to set the timeframe context for the underlying game selection!!!
        """
        self.game_info = game_info
        self.team      = team
        self.filters   = filters.copy() if filters else []
        self.frozen    = False

        # the following filters are considered part of the framework
        self.filters.append(_AnlyFilterPriTeam(self.team))
        self.filters.append(_AnlyFilterTimeframe(self.game_info.datetime))
        self.filters.append(_AnlyFilterRevChron())

    def add_filter(self, filter: AnlyFilter) -> None:
        if self.frozen:
            raise LogicError("Cannot add filters after analysis is frozen")
        self.filters.append(filter)

    @property
    def stats(self) -> AnlyStats:
        if not self._stats:
            self.compute_stats()
        return self._stats

    def compute_stats(self) -> None:
        """Compute stats based on analysis filters added.

        The current implementation retrieves all applicable games from the
        database (without any database-level aggregation), and iterates over
        the results to compute the stats.
        """
        query = Game.select()

        # REVISIT: not sure we need to do this, but may make things easier to
        # debug regardless!
        self.filters.sort(key=lambda f: f.type.value)

        for filter in self.filters:
            query = filter.apply(query)

        print(query_to_string(query))
        games       = list(query.execute())
        wins        = []
        losses      = []
        ties        = []
        ats_wins    = []
        pts_for     = 0
        pts_against = 0
        yds_for     = 0
        yds_against = 0
        tos_for     = 0
        tos_against = 0

        for game in games:
            if game.is_tie:
                ties.append(game)
            elif game.winner == self.team:
                wins.append(game)
            else:
                losses.append(game)

            is_home = game.home_team == self.team
            is_away = not is_home

            if game.pt_spread is not None:
                if is_home and game.home_vs_spread > 0.0:
                    ats_wins.append(game)
                elif is_away and game.away_vs_spread > 0.0:
                    ats_wins.append(game)

            # NOTE: this could probably be done more neatly using something
            # like `collection.Counter`, but not really worth doing unless/
            # until adding tons more stats here
            home_stats  = (game.home_pts, game.home_yds, game.home_tos)
            away_stats  = (game.away_pts, game.away_yds, game.away_tos)
            my_stats    = home_stats if is_home else away_stats
            opp_stats   = away_stats if is_home else home_stats

            pts_for     += my_stats[0]
            pts_against += opp_stats[0]
            yds_for     += my_stats[1]
            yds_against += opp_stats[1]
            tos_for     += my_stats[2]
            tos_against += opp_stats[2]

        self._stats = AnlyStats._make((games,
                                       wins,
                                       losses,
                                       ties,
                                       ats_wins,
                                       pts_for,
                                       pts_against,
                                       yds_for,
                                       yds_against,
                                       tos_for,
                                       tos_against))
        self.frozen = True
