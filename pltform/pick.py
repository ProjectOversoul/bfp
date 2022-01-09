# -*- coding: utf-8 -*-

from .team import Team

class Pick:
    """Pick for an individual game, whether based on external data or computation from
    an internal algorithm
    """
    su_winner:  Team
    ats_winner: Team
    margin:     float  # must be greater than 0.0
