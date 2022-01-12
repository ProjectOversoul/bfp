# -*- coding: utf-8 -*-

from os import environ
from typing import Any, TextIO
from collections.abc import Iterable

from peewee import query_to_string

from .core import cfg, log
from .game import Game
from .pick import Pick
from .swami import Swami

POOL_CONFIG = environ.get('BFP_POOL_CONFIG') or 'pools.yml'
cfg.load(POOL_CONFIG)

#############
# RunResult #
#############

class RunResult:
    su_pct:  float
    ats_pct: float

    def get_su_score(self) -> float:
        """Return straight-up score for pool result
        """
        pass

    def get_ats_score(self) -> float:
        """Return against-the-spread score for pool result
        """
        pass

    def get_aggregate_score(self) -> float:
        """Return aggregate score for pool result
        """
        pass

##############
# PoolResult #
##############

class PoolResult:
    su_pct:  float
    ats_pct: float

    def get_su_score(self) -> float:
        """Return straight-up score for pool result
        """
        pass

    def get_ats_score(self) -> float:
        """Return against-the-spread score for pool result
        """
        pass

    def get_aggregate_score(self) -> float:
        """Return aggregate score for pool result
        """
        pass

###########
# PoolRun #
###########

class PoolRun:
    """Run a pool for a specified timeframe (i.e. complete or partial season)
    """
    swamis:      list[Swami]
    season:      int
    weeks:       list[int] | None
    swami_picks: dict[Swami, dict[Game, Pick]]
    game_picks:  dict[Game, dict[Swami, Pick]]
    results:     dict[Swami, RunResult]

    def __init__(self, swamis: Iterable[Swami], season: int, weeks: Iterable[int] = None):
        """Run pool for the specified season, optionally narrowed to specific
        weeks within the season.  Note that special values for playoff weeks
        are defined using the `game.Week` enum, and `game.PLAYOFF_WEEKS` may
        be used to represent the set of all playoff weeks.
        """
        if weeks is not None:
            weeks = list(weeks)
        self.swamis      = list(swamis)
        self.season      = season
        self.weeks       = weeks
        self.swami_picks = {}
        self.game_picks  = {}

        for swami in self.swamis:
            self.swami_picks[swami] = {}

    @property
    def winner(self) -> Swami:
        return next(iter(self.results))

    def run(self) -> None:
        query = Game.select().where(Game.season == self.season)
        if self.weeks:
            query = query.where(Game.weeks << self.weeks)
        query = query.order_by(Game.season, Game.week, Game.datetime)

        log.debug("Pool games SQL: " + query_to_string(query))
        games = query.execute()

        for game in games:
            self.game_picks[game] = {}
            for swami in self.swamis:
                pick = swami.get_pick(game.get_info())
                self.swami_picks[swami][game] = pick
                self.game_picks[game][swami] = pick

    def compute_results(self):
        pass

    def get_results(self) -> list[dict[Swami, PoolResult]]:
        """Return dictionary of pool results, ordered by aggregate score (descending)
        """
        pass

    def print_results(self, file: TextIO = None) -> None:
        pass

########
# Pool #
########

class Pool:
    """Pool on game predictions between swamis
    """
    name:   str
    swamis: dict[str, Swami]  # indexed by name (do we need to do this???)
    runs:   list[PoolRun]

    def __init__(self, name: str, **kwargs: Any):
        """Note that the swamis for this pool are generally specified in the
        config file entry, but may be overridden in `kwargs`
        """
        pools = cfg.config('pools')
        if name not in pools:
            raise RuntimeError(f"Pool '{name}' is not known")
        pool_info = pools[name]
        # if `swamis` specified in `kwargs`, replaces config file list (no merging)
        swamis = kwargs.pop('swamis', None) or pool_info.get('swamis')

        self.name   = name
        self.swamis = {}
        self.runs   = []
        # idx is used below as a count of the inbound swamis
        for idx, swami in enumerate(swamis):
            if isinstance(swami, str):
                swami = Swami.new(swami)
            self.swamis[swami.name] = swami
        if len(self.swamis) < 1:
            raise RuntimeError("At least one swami must be specified")
        if len(self.swamis) < idx + 1:
            raise RuntimeError("Swami names must be unique")

    def get_run(self, season: int, weeks: Iterable[int] = None) -> PoolRun:
        """Initializes and returns the pool run instance; it is up to the caller
        to actually run it.
        """
        run = PoolRun(self.swamis.values(), season, weeks)
        self.runs.append(run)

        return run
