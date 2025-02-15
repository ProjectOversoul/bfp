# -*- coding: utf-8 -*-

from ..core import ConfigError, ImplementationError
from ..game import GameInfo, Pick
from ..analysis import Analysis, AbstrAnlyFilter, AnlyFilterVenue, AnlyFilterSeasons, AnlyFilterGames
from .base import Swami

class SwamiCyberBasic(Swami):
    """Cyber Swami abstract class based on basic `Analysis` class (and `AnlyFilter`s)
    and configuration parameters for games/seasons, and selection "criteria".
    """
    num_games:   int
    num_seasons: int
    consider_venue: bool
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

    def make_pick(self, game_info: GameInfo) -> Pick | None:
        """Implement algorithm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predictions and confidence for both SU and ATS
        """
        raise ImplementationError("Subclasses must override this method")

    def cyber_pick(self, game_info: GameInfo, filters: list[AbstrAnlyFilter] = None) -> Pick:
        """Common pick logic for CyberBasic Swamis, typically called from subclass `make_pick`
        implementations.  Applies the logic for configured number of games or seasons, as well
        as selection `criteria`.

        :param game_info: passed through from `make_pick()`
        :param filters: subclass-specific filters (applied on top of common logic)
        :return: pick based on first criterion to resolve
        """
        addl_filters = filters or []
        base_filters = []
        if self.num_seasons:
            base_filters.append(AnlyFilterSeasons(self.num_seasons))
        elif self.num_games:
            base_filters.append(AnlyFilterGames(self.num_games))
        else:
            raise RuntimeError("Either `num_seasons` or `num_games` must be specified")
        home_team  = game_info.home_team
        away_team  = game_info.away_team
        if self.consider_venue:
            home_filter = AnlyFilterVenue(AnlyFilterVenue.HOME)
            away_filter = AnlyFilterVenue(AnlyFilterVenue.AWAY)
            team_filter = {home_team: home_filter,
                           away_team: away_filter}
            base_filters.append(team_filter)

        analysis = Analysis(game_info)
        for base_filter in base_filters:
            analysis.add_filter(base_filter)
        
        for filter in addl_filters:
            analysis.add_filter(filter)

        home_stats = analysis.get_stats(home_team)
        away_stats = analysis.get_stats(away_team)
        total_pts  = (home_stats.total_pts + away_stats.total_pts) / 2.0

        for crit in self.criteria:
            stat = self.CRIT_MAP[crit]
            if getattr(home_stats, stat) > getattr(away_stats, stat):
                winner     = home_team
                margin     = home_stats.pts_margin
                my_spread  = -margin
                home_fav   = True
                break
            elif getattr(home_stats, stat) < getattr(away_stats, stat):
                winner     = away_team
                margin     = away_stats.pts_margin
                my_spread  = margin
                home_fav   = False
                break
        else:
            # all else being equal, pick the home team
            winner     = home_team
            margin     = home_stats.pts_margin
            my_spread  = -margin
            home_fav   = True

        # This is a little messy, but we use `my_spread` as computed above for
        # the ATS pick, then do some doctoring to ensure that the return value
        # is consistent with the SU pick in terms of sign and being non-zero;
        # I think this means it is possible to come up with paradoxical picks,
        # but that's the way this algorithm works (at least, for now).
        if game_info.pt_spread is not None:
            ats_winner = away_team if my_spread > game_info.pt_spread else home_team
        else:
            ats_winner = None
        margin = max(round(margin), 1)
        my_spread = -margin if home_fav else margin
        conf = (margin, abs(my_spread - game_info.pt_spread))
        return Pick(winner, ats_winner, my_spread, margin, round(total_pts), *conf)
