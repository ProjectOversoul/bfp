# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .base import Swami

class SwamiVsConf(Swami):
    """Rudimentary prediction based on last two seasons' record against conference
    """
    name = "Rudi 7"
    desc = "Based on last two seasons' record against conference"

    def __init__(self, conf: str):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        pass
