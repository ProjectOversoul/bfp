# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .base import Swami

class SwamiFiveThirtyEight(Swami):
    """History of predictions from the fivethirtyeight.com website
    """
    name = "FiveThirtyEight"
    desc = "History of predictions from fivethirtyeight.com"

    def __init__(self):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algoritm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        pass
