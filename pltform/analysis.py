# -*- coding: utf-8 -*-

from .game import Game

###########
# Filters #
###########

class AnlyFilter:
    """Base class for analysis filters
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterVenue(AnlyFilter):
    """Filter specifying home vs. away games to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterTeam(AnlyFilter):
    """Filter specifying opposing team to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterConf(AnlyFilter):
    """Filter specifying opponent team conference to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterDiv(AnlyFilter):
    """Filter specifying opponent team division to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterGames(AnlyFilter):
    """Filter specifying number of qualitfying games to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterSeasons(AnlyFilter):
    """Filter specifying number of seasons to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterWeeks(AnlyFilter):
    """Filter specifying which weeks within the season to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterRecord(AnlyFilter):
    """Filter specifying the current/opponent team point-in-time season
    records for games to evaluate
    """
    def __init__(self, **kwargs):
        pass

class AnlyFilterSpread(AnlyFilter):
    """Filter specifying the spread (relative to current team) for games
    to evaluate
    """
    def __init__(self, **kwargs):
        pass

#########
# Stats #
#########

class AnlyStats(NamedTuple):
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
    filters: list[AnlyFilter]
    frozen:  bool = False
    _stats:  AnlyStats

    def __init__(self, team: Team, filters: Iterable[AnlyFilter] = None):
        self.team    = team
        self.filters = filters or []

    def add_filter(self, filter: AnlyFilter) -> None:
        if self.frozen:
            raise LogicError("Cannot add filters after analysis is frozen")
        self.filters.add(filter)

    @property
    def stats(self) -> AnlyStats:
        if not self._stats:
            self.compute_stats()
        return self._stats

    def compute_stats(self) -> None:
        self._stats = AnlyStats._make([None] * AnlyStats.size())
        self.frozen = True
