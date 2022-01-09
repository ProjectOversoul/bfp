# -*- coding: utf-8 -*-

from typing import TextIO
from collections.abc import Iterable

from .swami import Swami

##############
# CompResult #
##############

class CompResult:
    su_pct:  float
    ats_pct: float

    def get_su_score(self) -> float:
        """Return straight-up score for competition result
        """
        pass

    def get_ats_score(self) -> float:
        """Return against-the-spread score for competition result
        """
        pass

    def get_aggregate_score(self) -> float:
        """Return aggregate score for competition result
        """
        pass

###############
# Competition #
###############

class Competition:
    """Competition on game predictions between swamis
    """
    def __init__(self, swamis: Iterable[Swami], season: int, weeks: Iterable[int] = None):
        pass

    @property
    def winner(self) -> Swami:
        return self.get_results[0][0]

    def get_results(self) -> dict[Swami, CompResult]:
        """Return dictionary of competition results, ordered by aggregate score (descending)
        """
        pass

    def print_results(self, file: TextIO = None) -> None:
        pass
