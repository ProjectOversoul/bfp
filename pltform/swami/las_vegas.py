# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .ext_data import SwamiExtData

class SwamiLasVegas(SwamiExtData):
    """History of predictions based on Las Vegas odds
    """
    name = "Las Vegas"
    desc = "History of predictions based on Las Vegas odds"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
