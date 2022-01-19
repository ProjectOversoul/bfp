# -*- coding: utf-8 -*-

from ..core import ConfigError, ImplementationError
from ..game import GameInfo, Pick
from ..analysis import Analysis, AbstrAnlyFilter, AnlyFilterSeasons, AnlyFilterGames
from .base import Swami

class SwamiCyberBasic(Swami):
    """Cyber Swami abstract class based on basic `Analysis` class (and `AnlyFilter`s)
    and configuration parameters for games/seasons, and selection "criteria".
    """
    num_games:   int
    num_seasons: int
    criteria:    list[str]  # see `CRIT_MAP` for valid values

    CRIT_MAP = {'games':       'num_games',
                'wins':        'num_wins',
                'win_pct':     'win_pct',
                'ats_wins':    'num_ats_wins',
                'ats_win_pct': 'ats_win_pct',
                'pts':         'pts_margin',
                'yds':         'yds_margin',
                'tos':         'tos_margin'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.num_games and not self.num_seasons:
            raise RuntimeError("Either `num_games` or `num_seasons` must be specified")
        for crit in self.criteria:
            if crit not in self.CRIT_MAP:
                raise ConfigError(f"Invalid criterion '{crit}' in `criteria`")

    def cyber_pick(self, game_info: GameInfo, filters: list[AbstrAnlyFilter] = None) -> Pick:
        """Common pick logic for CyberBasic Swamis.  Applies the logic for configured
        number of games or seasons, as well as selection `criteria`.

        :param game_info: passed through from `get_pick()`
        :param filters: subclass-specific filters (applied on top of common logic)
        :return: pick based on first criterion to resolve
        """
        addl_filters = filters or []
        if self.num_seasons:
            base_filter = AnlyFilterSeasons(self.num_seasons)
        elif self.num_games:
            base_filter = AnlyFilterGames(self.num_games)
        else:
            raise RuntimeError("Either `num_seasons` or `num_games` must be specified")

        analysis = Analysis(game_info)
        analysis.add_filter(base_filter)
        for filter in addl_filters:
            analysis.add_filter(filter)

        home_team  = game_info.home_team
        away_team  = game_info.away_team
        home_stats = analysis.get_stats(home_team)
        away_stats = analysis.get_stats(away_team)
        total_pts  = (home_stats.total_pts + away_stats.total_pts) / 2.0

        for crit in self.criteria:
            stat = self.CRIT_MAP[crit]
            if getattr(home_stats, stat) > getattr(away_stats, stat):
                winner    = home_team
                margin    = home_stats.pts_margin
                my_spread = -margin
                break
            elif getattr(home_stats, stat) < getattr(away_stats, stat):
                winner    = away_team
                margin    = away_stats.pts_margin
                my_spread = margin
                break
        else:
            # all else being equal, pick the home team
            winner = home_team
            margin = home_stats.pts_margin

        ats_winner = away_team if my_spread > game_info.pt_spread else home_team
        return Pick(winner, ats_winner, max(round(margin), 1), round(total_pts))
