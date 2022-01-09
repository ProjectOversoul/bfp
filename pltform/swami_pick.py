# -*- coding: utf-8 -*-

from .swami import Swami
from .game import Game
from .pick import Pick

class SwamiPick:
    """Pick by an individual swami for an individual game
    """
    swami:      Swami
    game:       Game
    pick:       Pick
