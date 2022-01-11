# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .base import Swami

class SwamiVsTeam(Swami):
    """Rudimentary prediction based on last matchup between teams
    """
    name = "Rudi 4"
    desc = "Based on last matchup between teams"

    def __init__(self, opp: Team):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        pass
