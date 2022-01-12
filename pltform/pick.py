# -*- coding: utf-8 -*-

from typing import NamedTuple

from .team import Team

class Pick(NamedTuple):
    """Pick for an individual game, whether based on external data or computation from
    an internal algorithm
    """
    su_winner:  Team
    ats_winner: Team | None  # only if `pt_spread` is available
    pts_margin: int          # must be greater than 0
    total_pts:  int
