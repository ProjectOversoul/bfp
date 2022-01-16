# -*- coding: utf-8 -*-

from ..game import GameInfo, Pick
from .cyber import SwamiCyber

class SwamiVsAll(SwamiCyber):
    """Rudimentary prediction based on most recent games against any opponent
    """
    def get_pick(self, game_info: GameInfo) -> Pick:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        return self.cyber_pick(game_info)
