# -*- coding: utf-8 -*-

from typing import ClassVar

from ..team import Team
from ..game import GameInfo

class SwamiBase:
    """Abstract base class for football swami; each subclass is an implementation
    of football prediction algorithms
    """
    name: ClassVar[str]
    
    def __init__(self):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algoritm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: winning team and margin of victory
        """
        pass
