# -*- coding: utf-8 -*-

from typing import ClassVar, NamedTuple
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

class AnlyFilterVenue(AnlyFilter):
    """Filter specifying home vs. away games to evaluate
    """
    def __init__(self):
        pass

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

class AnlyFilterWeeks(AnlyFilter):
    """Filter specifying which weeks within the season to evaluate
    """
    def __init__(self):
        pass

class AnlyFilterRecord(AnlyFilter):
    """Filter specifying the current/opponent team point-in-time season
    records for games to evaluate
    """
    def __init__(self):
        pass

class AnlyFilterSpread(AnlyFilter):
    """Filter specifying the spread (relative to current team) for games
    to evaluate
    """
    def __init__(self):
        pass

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
    if no other team scope filters have been applied
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
        if not self.games:
            return -1.0
        return len(self.wins) / len(self.games) * 100.0

    @property
    def loss_pct(self) -> float:
        if not self.games:
            return -1.0
        return len(self.losses) / len(self.games) * 100.0

    @property
    def ats_pct(self) -> float:
        if not self.games:
            return -1.0
        return len(self.ats_wins) / len(self.games) * 100.0

    @property
    def pts_margin(self) -> float:
        """Average points margin
        """
        if not self.games:
            return -1.0
        return (self.pts_for - self.pts_against) / len(self.games)

    @property
    def total_pts(self) -> float:
        """Average points margin
        """
        if not self.games:
            return -1.0
        return (self.pts_for + self.pts_against) / len(self.games)

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
    team_scope:   dict[Team, bool]
    frozen:       bool

    def __init__(self, game_ctx: GameCtx, filters: list[AnlyFilter] = None):
        filters = filters or []
        teams   = (game_ctx.home_team, game_ctx.away_team)

        self.game_ctx     = game_ctx
        self.team_filters = {t: filters.copy() for t in teams}
        self.team_stats   = {t: None for t in teams}
        self.team_scope   = {t: False for t in teams}
        self.frozen       = False

        # the following filters are considered part of the framework
        self.add_filter(_AnlyFilterTimeframe())
        self.add_filter(_AnlyFilterRevChron())

    def add_filter(self, filter: AnlyFilter) -> None:
        """Add the same filter to the analysis for both teams in the game
        context
        """
        if self.frozen and type(filter) not in FRAMEWORK_FILTERS:
            raise LogicError("Cannot add filters after analysis is frozen")
        for team in self.team_filters:
            self.team_filters[team].append(filter)

    def add_filters(self, filters: dict[Team, AnlyFilter]) -> None:
        """Add different filters to the analysis for the two teams in the
        game context, indexed by `Team`
        """
        for team, filter in filters.items():
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
            query = filter.apply(self.game_ctx, team, query)
            if type(filter) in TEAM_SCOPE_FILTERS:
                self.team_scope[team] = True

        for team in self.team_scope:
            if not self.team_scope[team]:
                self.add_filters({team: _AnlyFilterSelf()})
                self.team_scope[team] = True

        log.debug(f"{team} SQL: " + query_to_string(query))
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
