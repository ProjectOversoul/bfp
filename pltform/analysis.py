# -*- coding: utf-8 -*-

from typing import ClassVar, NamedTuple
from collections import Counter
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
        raise ImplementationError("Should not be called by subclass `__init__`")

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        raise ImplementationError("Must be implemented by subclass")

# "abstract filter" represents both variants of a filter specification--either a
# single filter to be applied to both teams; or a map of filters, indexed by team,
# to be applied selectively
AbstrAnlyFilter = AnlyFilter | dict[Team, AnlyFilter]

class AnlyFilterVenue(AnlyFilter):
    """Filter specifying home vs. away games to evaluate
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterTeam(AnlyFilter):
    """Filter specifying opposing team to evaluate
    """
    type = FilterType.WHERE

    opp_team: Team

    def __init__(self, opp_team: Team):
        self.opp_team = opp_team

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        return query.where(((Game.home_team == str(my_team)) &
                            (Game.away_team == str(self.opp_team))) |
                           ((Game.home_team == str(self.opp_team)) &
                            (Game.away_team == str(my_team))))

class AnlyFilterDiv(AnlyFilter):
    """Filter specifying opponent team division to evaluate
    """
    type = FilterType.WHERE

    div: str

    def __init__(self, div: str):
        self.div = div

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        HomeTeam = Team.alias()
        AwayTeam = Team.alias()
        return (query
                .join(HomeTeam, on=(HomeTeam.code == Game.home_team))
                .join(AwayTeam, on=(AwayTeam.code == Game.away_team))
                .where(((Game.home_team == str(my_team)) &
                        (AwayTeam.div == self.div)) |
                       ((Game.away_team == str(my_team)) &
                        (HomeTeam.div == self.div))))

class AnlyFilterConf(AnlyFilter):
    """Filter specifying opponent team conference to evaluate
    """
    type = FilterType.WHERE

    conf: str

    def __init__(self, conf: str):
        self.conf = conf

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        HomeTeam = Team.alias()
        AwayTeam = Team.alias()
        return (query
                .join(HomeTeam, on=(HomeTeam.code == Game.home_team))
                .join(AwayTeam, on=(AwayTeam.code == Game.away_team))
                .where(((Game.home_team == str(my_team)) &
                        (AwayTeam.conf == self.conf)) |
                       ((Game.away_team == str(my_team)) &
                        (HomeTeam.conf == self.conf))))

class AnlyFilterWeeks(AnlyFilter):
    """Filter specifying which weeks within the season to evaluate
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterDayOfWeek(AnlyFilter):
    """Filter specifying which day(s) of the week for games to evaluate
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterRecord(AnlyFilter):
    """Filter specifying the current/opponent team point-in-time season records
    for games to evaluate
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterRanking(AnlyFilter):
    """Filter specifying the current/opponent team point-in-time season ranking
    (e.g. total offense/defense) for games to evaluate
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterSpread(AnlyFilter):
    """Filter specifying the points spread (relative to current team) for games
    to evaluate
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterOutcome(AnlyFilter):
    """Filter specifying outcome of the games to evaluate (i.e. win, loss, or tie
    by the target team)
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterStatMargin(AnlyFilter):
    """Filter specifying a stats margin for games to consider (e.g. "games won by
    less than 7 points")
    """
    def __init__(self):
        raise ImplementationError("Not yet implemented")

class AnlyFilterGames(AnlyFilter):
    """Filter specifying number of qualifying games to evaluate
    """
    type = FilterType.LIMIT

    games: int

    def __init__(self, games: int):
        self.games = games

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        return query.limit(self.games)

class AnlyFilterSeasons(AnlyFilter):
    """Filter specifying number of seasons to evaluate
    """
    type = FilterType.WHERE

    seasons: int

    def __init__(self, seasons: int):
        """Note that `seasons=1` indicates the current season, regardless of
        where in the season we currently are; thus, `seasons=2` indicates last
        season plus this season so far, etc.
        """
        self.seasons = seasons

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        end = ctx.season
        start = end - self.seasons + 1
        return query.where(Game.season.between(start, end))

class _AnlyFilterTimeframe(AnlyFilter):
    """Filter specifying the timeframe for the analysis (games considered must be
    earlier than the context datetime), applied implicitly by the framework.
    """
    type = FilterType.WHERE

    def __init__(self):
        pass

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        return query.where(Game.datetime < str(ctx.datetime))

class _AnlyFilterRevChron(AnlyFilter):
    """Filter specifying reverse chronological order for results so that the
    LIMIT filters work right, applied implicitly by the framework.
    """
    type = FilterType.ORDER_BY

    def __init__(self):
        pass

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        return query.order_by(Game.datetime.desc())

class _AnlyFilterSelf(AnlyFilter):
    """Filter specifying the target team scope, applied implicitly by the framework
    (if no other team scope filters have been applied).
    """
    type = FilterType.WHERE

    def __init__(self):
        pass

    def apply(self, ctx: GameCtx, my_team: Team, query: ModelSelect) -> ModelSelect:
        return query.where((Game.home_team == str(my_team)) |
                           (Game.away_team == str(my_team)))

#########
# Stats #
#########

class StatsCounter(Counter):
    """Emulates a list that looks like `[pts, yds, tos]`, except it does
    some tabulation for us.
    """
    @staticmethod
    def empty() -> 'StatsCounter':
        return StatsCounter(0, 0, 0)

    def __init__(self, pts: int, yds: int, tos: int):
        super().__init__({0: pts, 1: yds, 2: tos})

class AnlyStats(NamedTuple):
    """Note that we record `games`, `wins`, `losses`, etc. as lists of games
    (rather than just the count), so the underlying detail-level information
    is readily available to the analysis class.  The count for each type of
    result is available as a derived property
    """
    games:       list[Game]
    wins:        list[Game]
    losses:      list[Game]
    ties:        list[Game]
    ats_wins:    list[Game]  # wins against the spread (beat or cover)
    pts_for:     int
    pts_against: int
    yds_for:     int
    yds_against: int
    tos_for:     int  # committed by current team
    tos_against: int  # committed by opponent

    @property
    def num_games(self) -> int:
        return len(self.games)

    @property
    def num_wins(self) -> int:
        return len(self.wins)

    @property
    def num_losses(self) -> int:
        return len(self.losses)

    @property
    def num_ties(self) -> int:
        return len(self.ties)

    @property
    def num_ats_wins(self) -> int:
        return len(self.ats_wins)

    @property
    def win_pct(self) -> float:
        if not self.games:
            return -1.0
        return len(self.wins) / len(self.games) * 100.0

    @property
    def loss_pct(self) -> float:
        if not self.games:
            return -1.0
        return len(self.losses) / len(self.games) * 100.0

    @property
    def ats_win_pct(self) -> float:
        if not self.games:
            return -1.0
        return len(self.ats_wins) / len(self.games) * 100.0

    @property
    def pts_margin(self) -> float:
        """Average points margin for games evaluated
        """
        if not self.games:
            return -1.0
        return (self.pts_for - self.pts_against) / len(self.games)

    @property
    def total_pts(self) -> float:
        """Average total points for games evaluated
        """
        if not self.games:
            return -1.0
        return (self.pts_for + self.pts_against) / len(self.games)

    @property
    def yds_margin(self) -> float:
        """Average yards margin for games evaluated
        """
        if not self.games:
            return -1.0
        return (self.yds_for - self.yds_against) / len(self.games)

    @property
    def total_yds(self) -> float:
        """Average total yards for games evaluated
        """
        if not self.games:
            return -1.0
        return (self.yds_for + self.yds_against) / len(self.games)

    @property
    def tos_margin(self) -> float:
        """Average turnover margin for games evaluated

        NOTE: this stat is computed to represent take-away differential (to use
        the proper sports term), as opposed to difference of turnovers *by* the
        teams, so that a higher number continues to indicate better performance
        (consistent with the other stats in this class)
        """
        if not self.games:
            return -1.0
        return (self.tos_against - self.tos_for) / len(self.games)

    @property
    def total_tos(self) -> float:
        """Average total turnovers for games evaluated
        """
        if not self.games:
            return -1.0
        return (self.tos_for + self.tos_against) / len(self.games)

############
# Analysis #
############

# the following filter classes narrow the scope to the target team, we
# need to make sure at least one of these is applied for each analysis
TEAM_SCOPE_FILTERS = {AnlyFilterTeam,
                      AnlyFilterDiv,
                      AnlyFilterConf,
                      _AnlyFilterSelf}

FRAMEWORK_FILTERS = {_AnlyFilterTimeframe,
                     _AnlyFilterRevChron,
                     _AnlyFilterSelf}

class Analysis:
    """Analysis object with stats for specified team and evaluation filters
    """
    game_ctx:     GameCtx
    team_filters: dict[Team, list[AnlyFilter]]
    team_stats:   dict[Team, AnlyStats | None]
    frozen:       bool

    def __init__(self, game_ctx: GameCtx):
        teams   = (game_ctx.home_team, game_ctx.away_team)

        self.game_ctx     = game_ctx
        self.team_filters = {t: [] for t in teams}
        self.team_stats   = {t: None for t in teams}
        self.frozen       = False

        # the following filters are considered part of the framework
        self.add_filter(_AnlyFilterTimeframe())
        self.add_filter(_AnlyFilterRevChron())

    def add_filter(self, filter: AbstrAnlyFilter) -> None:
        """Add filter or team filter map to the analysis for the teams in
        the game context
        """
        if isinstance(filter, dict):
            return self.add_team_filter(filter)
        assert isinstance(filter, AnlyFilter)
        if self.frozen and type(filter) not in FRAMEWORK_FILTERS:
            raise LogicError("Cannot add filters after analysis is frozen")
        # apply the same filter to both teams
        for team in self.team_filters:
            self.team_filters[team].append(filter)

    def add_team_filter(self, team_filter: dict[Team, AnlyFilter]) -> None:
        """Add map of filters (indexed by `Team`) to the analysis for the
        teams in the game context
        """
        for team, filter in team_filter.items():
            if self.frozen and type(filter) not in FRAMEWORK_FILTERS:
                raise LogicError("Cannot add filters after analysis is frozen")
            self.team_filters[team].append(filter)

    def get_stats(self, team: Team) -> AnlyStats:
        if team not in self.team_stats:
            raise LogicError(f"Team '{team}' not in game_id {self.game_ctx.game_id}")
        if not self.team_stats[team]:
            # first access to stats locks out changes to filters
            self.frozen = True
            self.team_stats[team] = self.compute_stats(team)
            log.debug(f"{team} stats: {self.team_stats[team]}")
        return self.team_stats[team]

    def compute_stats(self, anly_team: Team) -> AnlyStats:
        """Compute stats based on analysis filters added.

        The current implementation retrieves all applicable games from the
        database (without any database-level aggregation), and iterates over
        the results to compute the stats.
        """
        for team_i, filters in self.team_filters.items():
            team_scope = False
            for filter in filters:
                if type(filter) in TEAM_SCOPE_FILTERS:
                    team_scope = True
            if not team_scope:
                self.add_team_filter({team_i: _AnlyFilterSelf()})

        query = Game.select()

        # REVISIT: not sure we need to do this, but may make things easier to
        # debug regardless!
        self.team_filters[anly_team].sort(key=lambda f: f.type.value)

        for filter in self.team_filters[anly_team]:
            query = filter.apply(self.game_ctx, anly_team, query)

        log.debug(f"{anly_team} SQL: " + query_to_string(query))
        games         = list(query.execute())
        wins          = []
        losses        = []
        ties          = []
        ats_wins      = []
        stats_for     = StatsCounter.empty()
        stats_against = StatsCounter.empty()

        for game in games:
            if game.is_tie:
                ties.append(game)
            elif game.winner == anly_team:
                wins.append(game)
            else:
                losses.append(game)

            is_home = game.home_team == anly_team
            is_away = not is_home

            if game.pt_spread is not None:
                if is_home and game.home_vs_spread > 0.0:
                    ats_wins.append(game)
                elif is_away and game.away_vs_spread > 0.0:
                    ats_wins.append(game)

            home_stats  = StatsCounter(game.home_pts, game.home_yds, game.home_tos)
            away_stats  = StatsCounter(game.away_pts, game.away_yds, game.away_tos)
            my_stats    = home_stats if is_home else away_stats
            opp_stats   = away_stats if is_home else home_stats

            stats_for     += my_stats
            stats_against += opp_stats

        return AnlyStats._make((games,
                                wins,
                                losses,
                                ties,
                                ats_wins,
                                stats_for[0],
                                stats_against[0],
                                stats_for[1],
                                stats_against[1],
                                stats_for[2],
                                stats_against[2]))
