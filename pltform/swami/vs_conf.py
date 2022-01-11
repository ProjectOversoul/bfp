# -*- coding: utf-8 -*-

from ..team import Team
from ..game import GameInfo
from ..analysis import Analysis, AnlyFilterGames, AnlyFilterSeasons, AnlyFilterConf
from .base import Swami

class SwamiVsConf(Swami):
    """Rudimentary prediction based on most recent games against a specific
    opponent team
    """
    num_games:   int
    num_seasons: int

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        if not self.num_games and not self.num_seasons:
            raise RuntimeError("Either `num_games` or `num_seasons` must be specified")

    def pick_winner(self, game_info: GameInfo) -> tuple[Team, int]:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        if self.num_seasons:
            base_filter = AnlyFilterSeasons(self.num_seasons)
        elif self.num_games:
            base_filter = AnlyFilterGames(self.num_games)
        else:
            raise RuntimeError("Either `num_seasons` or `num_games` must be specified")
        home_team = game_info.home_team
        away_team = game_info.away_team
        opp_filters = {home_team: AnlyFilterConf(away_team.conf),
                       away_team: AnlyFilterConf(home_team.conf)}

        analysis = Analysis(game_info, [base_filter])
        analysis.add_filters(opp_filters)
        home_stats = analysis.get_stats(home_team)
        away_stats = analysis.get_stats(away_team)

        if len(home_stats.wins) > len(away_stats.wins):
            winner = game_info.home_team
            margin = home_stats.pts_margin
        elif len(home_stats.wins) < len(away_stats.wins):
            winner = game_info.away_team
            margin = away_stats.pts_margin
        elif home_stats.pts_margin >= away_stats.pts_margin:
            # favor home team in case of tie on margin
            winner = home_team
            margin = home_stats.pts_margin
        else:
            winner = away_team
            margin = away_stats.pts_margin

        return winner, max(round(margin), 1)
