# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .base import Swami

class SwamiVsDiv(Swami):
    """Rudimentary prediction based on last two seasons' record against division
    """
    name = "Rudi 8"
    desc = "Based on last two seasons' record against division"

    def __init__(self, div: str):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        pass
