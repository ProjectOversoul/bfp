# -*- coding: utf-8 -*-

from typing import ClassVar, NamedTuple
from datetime import datetime
from enum import Enum

from peewee import ModelSelect, query_to_string

from .core import log, LogicError, ImplementationError
from .team import Team
from .game import Game, GameCtx

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
      - represent dependencies (or implicitly invoke)
      - represent incompatibilities (and how to signal)
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
    """Filter specifying number of qualifying games to evaluate
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
    game_ctx:     GameCtx
    team_filters: dict[Team, list[AnlyFilter]]
    team_stats:   dict[Team, AnlyStats | None]
    frozen:       bool

    def __init__(self, game_ctx: GameCtx, filters: list[AnlyFilter] = None):
        filters = filters or []
        teams   = (game_ctx.home_team, game_ctx.away_team)

        self.game_ctx     = game_ctx
        self.team_filters = {t: filters.copy() for t in teams}
        self.team_stats   = {t: None for t in teams}
        self.frozen       = False

        # the following filters are considered part of the framework
        self.add_filters({t: _AnlyFilterPriTeam(t) for t in teams})
        self.add_filter(_AnlyFilterTimeframe(self.game_ctx.datetime))
        self.add_filter(_AnlyFilterRevChron())

    def add_filter(self, filter: AnlyFilter) -> None:
        if self.frozen:
            raise LogicError("Cannot add filters after analysis is frozen")
        for team in self.team_filters:
            self.team_filters[team].append(filter)

    def add_filters(self, filters: dict[Team, AnlyFilter]) -> None:
        if self.frozen:
            raise LogicError("Cannot add filters after analysis is frozen")
        for team in self.team_filters:
            self.team_filters[team].append(filters[team])

    def get_stats(self, team: Team) -> AnlyStats:
        if team not in self.team_stats:
            raise LogicError(f"Team '{team}' not in game_id {self.game_ctx.game_id}")
        if not self.team_stats[team]:
            # first access to stats locks out changes to filters
            self.frozen = True
            self.team_stats[team] = self.compute_stats(team)
        return self.team_stats[team]

    def compute_stats(self, team: Team) -> AnlyStats:
        """Compute stats based on analysis filters added.

        The current implementation retrieves all applicable games from the
        database (without any database-level aggregation), and iterates over
        the results to compute the stats.
        """
        query = Game.select()

        # REVISIT: not sure we need to do this, but may make things easier to
        # debug regardless!
        self.team_filters[team].sort(key=lambda f: f.type.value)

        for filter in self.team_filters[team]:
            query = filter.apply(query)

        log.debug(query_to_string(query))
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
            elif game.winner == team:
                wins.append(game)
            else:
                losses.append(game)

            is_home = game.home_team == team
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

        return AnlyStats._make((games,
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
