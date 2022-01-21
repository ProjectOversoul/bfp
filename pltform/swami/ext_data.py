# -*- coding: utf-8 -*-

from peewee import DoesNotExist

from ..game import GameInfo, Pick
from .base import Swami, SwamiPick

class SwamiExtData(Swami):
    """Swami type based on external data source for current and/or historical picks,
    whether originating from people or machines.

    TBD: abstract design for defining external data sources and retrieving data!!!
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_pick(self, game_info: GameInfo) -> Pick | None:
        """Implement algoritm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        try:
            swami_pick = (SwamiPick
                          .select()
                          .where(SwamiPick.swami_id == self.id,
                                 SwamiPick.game_id == game_info.id)
                          .order_by(SwamiPick.pick_ts.desc())
                          .get())
        except DoesNotExist:
            return None
        ret = swami_pick.get_pick()
        return ret
