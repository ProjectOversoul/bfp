# -*- coding: utf-8 -*-

from .game import Game

###########
# Filters #
###########

class AnlFilter:
    """Base class for analysis filters
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterVenue(AnlFilter):
    """Filter specifying home vs. away games to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterTeam(AnlFilter):
    """Filter specifying opposing team to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterConf(AnlFilter):
    """Filter specifying opponent team conference to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterDiv(AnlFilter):
    """Filter specifying opponent team division to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterGames(AnlFilter):
    """Filter specifying number of qualitfying games to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterSeasons(AnlFilter):
    """Filter specifying number of seasons to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterWeeks(AnlFilter):
    """Filter specifying which weeks within the season to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterRecord(AnlFilter):
    """Filter specifying the current/opponent team point-in-time season
    records for games to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlFilterSpread(AnlFilter):
    """Filter specifying the spread (relative to current team) for games
    to evaluate
    """
    def __init__(self, **kwargs):
        pass

#########
# Stats #
#########

class AnlStats(NamedTuple):
    games:       list[Game]
    wins:        list[Game]
    losses:      list[Game]
    ats_wins:    list[Game]  # wins against the spread (beat or cover)
    pts_for:     int
    pts_against: int
    yds_for:     int
    yds_against: int
    tos_for:     int
    tos_against: int

    @classmethod
    def size(cls) -> int:
        return len(cls._fields)

    @property
    def win_pct(self) -> float:
        pass

    @property
    def loss_pct(self) -> float:
        pass

    @property
    def ats_pct(self) -> float:
        pass

    @property
    def pts_margin(self) -> float:
        """Average points margin
        """
        pass

############
# Analysis #
############

class Analysis:
    """Analysis object with stats for specified team and evaluation filters
    """
    team:    Team
    filters: list[AnlFilter]
    frozen:  bool = False
    _stats:  AnlStats

    def __init__(self, team: Team, filters: Iterable[AnlFilter] = None):
        self.team    = team
        self.filters = filters or []

    def add_filter(self, filter: AnlFilter) -> None:
        if self.frozen:
            raise LogicError("Cannot add filters after analysis is frozen")
        self.filters.add(filter)

    @property
    def stats(self) -> AnlStats:
        if not self._stats:
            self.compute_stats()
        return self._stats

    def compute_stats(self) -> None:
        self._stats = AnlStats._make([None] * AnlStats.size())
        self.frozen = True
