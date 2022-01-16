# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .interact import SwamiInteract

class SwamiHuman(SwamiInteract):
    """Human swami, with picks coming from interactive web-app
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
