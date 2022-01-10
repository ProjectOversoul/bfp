# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from .base import Swami

class SwamiRudi1(Swami):
    """Rudimentary prediction based on last game played
    """
    name = "Rudi 1"
    desc = "Based on last game played"

    def __init__(self):
        pass

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        filters = []
        filters.add(AnlFilterGames(1))
        home_anl = Analysis(game_info.home_team, filters)
        away_anl = Analysis(game_info.away_team, filters)

        if home_anl.stats.wins > away_anl.stats.wins:
            winner = game_info.home_team
            margin = home_anl.pts_margin
        elif home_anl.stats.wins < away_anl.stats.wins:
            winner = game_info.away_team
            margin = away_anl.pts_margin
        elif home_anl.stats.pts_margin > away_anl.stats.pts_margin:
            winner = game_info.home_team
            margin = home_anl.pts_margin
        else:
            winner = game_info.away_team
            margin = away_anl.pts_margin

        return winner, max(margin, 1)
