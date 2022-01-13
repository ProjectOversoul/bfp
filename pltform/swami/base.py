# -*- coding: utf-8 -*-

from os import environ
from importlib import import_module

from ..core import cfg, ConfigError, ImplementationError
from ..game import GameInfo, Pick

SWAMI_CONFIG = environ.get('BFP_SWAMI_CONFIG') or 'swamis.yml'
cfg.load(SWAMI_CONFIG)

class Swami:
    """Abstract base class for football swami; each subclass is an implementation
    of football prediction algorithms, which are configurable via parameters.
    """
    name:     str
    about_me: str
    
    @classmethod
    def new(cls, swami_name: str, **kwargs: int) -> 'Swami':
        """Return instantiated `Swami` object based on configured swami, identified
        by name; note that the named swami entry may override base parameter values
        specified for the underlying implementation class.
        """
        swamis = cfg.config('swamis')
        if swami_name not in swamis:
            raise RuntimeError(f"Swami '{swami_name}' is not known")
        swami_info = swamis[swami_name]
        class_name = swami_info.get('swami_class')
        module_path = swami_info.get('module_path')
        swami_params = swami_info.get('swami_params') or {}
        swami_params['about_me'] = swami_info.get('about_me')
        if not class_name:
            raise ConfigError(f"`swami_class` not specified for swami '{swami_name}'")
        module = import_module(module_path)
        swami_class = getattr(module, class_name)
        if not issubclass(swami_class, cls):
            raise ConfigError(f"`{swami_class.__name__}` not subclass of `{cls.__name__}`")

        swami_params.update(kwargs)
        return swami_class(swami_name, **swami_params)

    def __init__(self, name: str, **kwargs: int):
        """Set parameter values as instance variables.  Note that param values may
        be defined in the `swami_classes` configuration, specified in the `swamis`
        entry, or overridden at instantiation time (see `new()`).

        Subclasses must invoke this base class constructor first, so that instance
        variables will be available for validation and/or additional configuration.
        """
        self.name = name
        self.about_me = kwargs.get('about_me')

        my_class_name = type(self).__name__
        swami_classes = cfg.config('swami_classes')
        if my_class_name not in swami_classes:
            raise ConfigError(f"Swami class `{my_class_name}` is not known")

        base_params = swami_classes[my_class_name].get('class_params')
        if not base_params:
            raise ConfigError(f"`class_params` missing for swami class `{my_class_name}`")
        for key, base_value in base_params.items():
            # note that empty values in kwargs should override base values
            setattr(self, key, kwargs[key] if key in kwargs else base_value)

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash((self.__class__, self.name))

    def get_pick(self, game_info: GameInfo) -> Pick:
        """Implement algoritm to pick winner of games

        :param game_info: context/schedule info for the game
        :return: predicted winning team and margin of victory
        """
        raise ImplementationError("Subclasses must override this method")
