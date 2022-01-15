# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .base import Swami

class SwamiHuman(Swami):
    """Human swami, with picks coming from interactive web-app
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algoritm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        pass
