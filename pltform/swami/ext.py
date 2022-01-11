# -*- coding: utf-8 -*-

from collections.abc import Iterable

from .base import Swami
from ..swami_pick import SwamiPick

class SwamiExt(Swami):
    """External swami based on history of picks/prediction data
    """
    pick_hist: list[SwamiPick]

    def load_pick_hist(self, season: int, weeks: Iterable[int] = None) -> None:
        pass
