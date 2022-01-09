# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .base import Swami

class SwamiRudi2(Swami):
    """Rudimentary prediction based on last two games played
    """
    name = "Rudi 2"
    desc = "Based on last two games played"

    def __init__(self):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        pass
