# -*- coding: utf-8 -*-

from ..game import GameInfo, Pick
from ..analysis import AnlyFilterConf
from .cyber_basic import SwamiCyberBasic

class SwamiVsConf(SwamiCyberBasic):
    """Rudimentary prediction based on most recent games against a specific
    opponent team
    """
    def get_pick(self, game_info: GameInfo) -> Pick | None:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        home_team = game_info.home_team
        away_team = game_info.away_team
        opp_filter = {home_team: AnlyFilterConf(away_team.conf),
                      away_team: AnlyFilterConf(home_team.conf)}

        return self.cyber_pick(game_info, [opp_filter])
