# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .ext_data import SwamiExtData

class SwamiFiveThirtyEight(SwamiExtData):
    """History of predictions from the fivethirtyeight.com website
    """
    name = "FiveThirtyEight"
    desc = "History of predictions from fivethirtyeight.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
