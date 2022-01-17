# -*- coding: utf-8 -*-

from ..game import GameInfo, Pick
from ..analysis import AnlyFilterTeam
from .cyber_basic import SwamiCyberBasic

class SwamiVsTeam(SwamiCyberBasic):
    """Rudimentary prediction based on most recent games against a specific
    opponent team
    """
    def get_pick(self, game_info: GameInfo) -> Pick:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        home_team = game_info.home_team
        away_team = game_info.away_team
        opp_filter = {home_team: AnlyFilterTeam(away_team),
                      away_team: AnlyFilterTeam(home_team)}

        return self.cyber_pick(game_info, [opp_filter])
