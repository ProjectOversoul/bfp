# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .ext import SwamiExt

class SwamiLasVegas(SwamiExt):
    """History of predictions based on Las Vegas odds
    """
    name = "Las Vegas"
    desc = "History of predictions based on Las Vegas odds"

    def __init__(self, **kwargs):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algoritm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        pass
