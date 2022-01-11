# -*- coding: utf-8 -*-

from ..core import ImplementationError
from ..team import Team
from ..game import GameInfo
from ..analysis import Analysis, AnlyFilterGames
from .base import Swami

class SwamiVsAll(Swami):
    """Rudimentary prediction based on most recent games against any opponent
    """
    num_games:   int
    num_seasons: int

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        if not self.num_games and not self.num_seasons:
            raise RuntimeError("Either `num_games` or `num_seasons` must be specified")
        # TODO: implement `num_seasons`!!!
        if self.num_seasons:
            raise ImplementationError("`num_seasons` not yet implemented")

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        filters = [AnlyFilterGames(self.num_games)]
        analysis = Analysis(game_info, filters)
        home_stats = analysis.get_stats(game_info.home_team)
        away_stats = analysis.get_stats(game_info.away_team)

        if home_stats.wins > away_stats.wins:
            winner = game_info.home_team
            margin = home_stats.pts_margin
        elif home_stats.wins < away_stats.wins:
            winner = game_info.away_team
            margin = away_stats.pts_margin
        elif home_stats.pts_margin >= away_stats.pts_margin:
            # favor home team in case of tie on margin
            winner = game_info.home_team
            margin = home_stats.pts_margin
        else:
            winner = game_info.away_team
            margin = away_stats.pts_margin

        return winner, max(round(margin), 1)
