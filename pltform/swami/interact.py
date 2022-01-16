# -*- coding: utf-8 -*-

from .base import Swami

class SwamiInteract(Swami):
    """Interactive swami type, either a human (e.g. through a web app), or an
    API interaction.

    TBD: abstract interface for integrating with interactive data sources!!!
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
