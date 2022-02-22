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
