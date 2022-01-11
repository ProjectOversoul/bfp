# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from ..analysis import Analysis, AnlyFilterGames
from .base import Swami

class SwamiRudi1(Swami):
    """Rudimentary prediction based on last game played
    """
    name = "Rudi 1"
    desc = "Based on last game played"

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        filters   = [AnlyFilterGames(1)]
        home_anly = Analysis(game_info, game_info.home_team, filters)
        away_anly = Analysis(game_info, game_info.away_team, filters)

        if home_anly.stats.wins > away_anly.stats.wins:
            winner = game_info.home_team
            margin = home_anly.stats.pts_margin
        elif home_anly.stats.wins < away_anly.stats.wins:
            winner = game_info.away_team
            margin = away_anly.stats.pts_margin
        elif home_anly.stats.pts_margin >= away_anly.stats.pts_margin:
            # favor home team in case of tie on margin
            winner = game_info.home_team
            margin = home_anly.stats.pts_margin
        else:
            winner = game_info.away_team
            margin = away_anly.stats.pts_margin

        return winner, max(round(margin), 1)
