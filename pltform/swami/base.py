# -*- coding: utf-8 -*-

from os import environ
from enum import Enum
from importlib import import_module
import json

from peewee import *

from ..utils import rankdata
from ..core import cfg, ConfigError
from ..db_core import BaseModel
from ..team import Team
from ..game import Game, Pick

SWAMI_CONFIG = environ.get('BFP_SWAMI_CONFIG') or 'swamis.yml'
cfg.load(SWAMI_CONFIG)

#############
# SwamiType #
#############

class SwamiType(Enum):
    """This is used primarily for documentation and reporting, not currently
    needed for instatiation or runtime logic
    """
    CYBER    = 'Cyber'
    EXT_DATA = 'External Data'
    INTERACT = 'Interactive'

#########
# Swami #
#########

SWAMI_TABLE = 'swami'

def swami_table(model_class):
    return SWAMI_TABLE

class Swami(BaseModel):
    """Abstract base class for football swami; each subclass is an implementation
    of football prediction algorithms, which are configurable via parameters.

    Note that `swami_type` is currently just informational (not needed for class
    instantiation), though a future can be imagined where it may be useful.
    to support `SwamiPicks` for "ext data" and "interactive" swami types!!!
    """
    name         = TextField(unique=True)
    about_me     = TextField(null=True)
    swami_type   = TextField(null=True)
    module_path  = TextField(null=True)
    swami_class  = TextField(null=True)
    swami_params = TextField(null=True)  # json representation of subclass instance vars

    game_pick: dict[int, Pick]  # indexed by game_id

    class Meta:
        table_function = swami_table

    @classmethod
    def get_class(cls, swami_name: str) -> type:
        """Return the subclass configured for the specified swami (by name)
        """
        swamis = cfg.config('swamis')
        if swami_name not in swamis:
            raise RuntimeError(f"Swami '{swami_name}' is not known")
        swami_info = swamis[swami_name]
        class_name = swami_info.get('swami_class')
        module_path = swami_info.get('module_path')
        if not class_name:
            raise ConfigError(f"`swami_class` not specified for swami '{swami_name}'")
        module = import_module(module_path)
        swami_class = getattr(module, class_name)
        if not issubclass(swami_class, cls):
            raise ConfigError(f"`{swami_class.__name__}` not subclass of `{cls.__name__}`")

        return swami_class

    @classmethod
    def get_class_info(cls) -> dict:
        """Return configuration information (metadata) for the class
        """
        my_class_name = cls.__name__
        swami_classes = cfg.config('swami_classes')
        if my_class_name not in swami_classes:
            raise ConfigError(f"Swami class `{my_class_name}` is not known")
        return swami_classes[my_class_name]

    @classmethod
    def get_by_name(cls, swami_name: str) -> 'Swami':
        """Convenience method for retrieving swami by name
        """
        return cls.get(cls.name == swami_name)

    def __new__(cls, **kwargs):
        """Instantiate the proper subclass, based on config file specification
        """
        if 'name' not in kwargs:
            raise RuntimeError("`name` must be specified")
        swami_class = cls.get_class(kwargs['name'])
        return super().__new__(swami_class)

    def __init__(self, **kwargs):
        """Set parameter values as instance variables.  Note that param values may
        be defined in the `swami_classes` configuration, specified in the `swamis`
        entry, or overridden at instantiation time (see `new()`).

        Subclasses must invoke this base class constructor first, so that instance
        variables will be available for validation and/or additional configuration.
        """
        super().__init__(**kwargs)
        params = json.loads(self.swami_params) if self.swami_params else {}

        class_info = self.__class__.get_class_info()
        if 'class_params' not in class_info:
            class_name = self.__class__.__name__
            raise ConfigError(f"`class_params` missing for swami class `{class_name}`")
        base_params = class_info.get('class_params') or {}
        for key, base_value in base_params.items():
            # note that empty values in `params` should override base values
            setattr(self, key, params[key] if key in params else base_value)

        self.game_pick = {}

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash((self.__class__, self.name))

    def process_week(self, season: int, week: int, pool_params: dict = None) -> None:
        """Retrieve and process swami's picks for the specified week, before caching
        them in the instance.  "Processing" means eliminating the lowest confidence
        picks, within the parameters of the current pool.
        """
        # TEMP: hardwired values for now; LATER, these should be passed in as part
        # of `pool_params`!!!
        ats_min_picks = 5
        ats_req_games = set()  # game_id's (derived from `ats_req_picks` in config)

        query = (SwamiPick
                 .select()
                 .join(Game, on=(Game.id == SwamiPick.game_id))
                 .where(SwamiPick.swami_id == self.id,
                        Game.season == season,
                        Game.week == week)
                 .order_by(SwamiPick.pick_ts.desc()))

        # ATTENTION: note that local version of `game_pick` differs in type from
        # `self.game_pick` (dict of `SwamiPick`s, rather than `Pick`s), since we
        # need the representation of picks to be mutable here, and immutable when
        # cached in the instance
        game_pick: dict[int, SwamiPick] = {}  # indexed by game_id
        for swami_pick in query.execute():
            game = swami_pick.game
            if game.id in game_pick:
                # REVISIT: `order_by` above ensures that only the latest SwamiPick for
                # a game is used, but the SU and ATS picks are intercoupled in the pick,
                # which is not great.  Thus, the picking logic for now needs to ensure
                # that changes to one subpool does not nullify the data for the other
                # (see comments in `SwamiPick.clear_ats()` below)!!!
                continue
            game_pick[game.id] = swami_pick

        swami_picks = list(game_pick.values())
        # do a little fudging if `ats_conf is None`--not pretty, but does what we
        # need it to (i.e. cache the pick so we don't have to requery later)
        ats_confs = [p.ats_conf or 0 for p in swami_picks]
        ats_conf_rank = rankdata(ats_confs, method='min')
        # NOTE: we are sorting this so that we are always adding picks in confidence-
        # ranked order, just in case we want to adjust the cut-off point on the fly
        # (e.g. due to mandatory picks, gaps in confidence-levels, etc.)
        for idx, rank in sorted(enumerate(ats_conf_rank), key=lambda s: s[1]):
            swami_pick = swami_picks[idx]
            game = swami_pick.game
            if rank > ats_min_picks and game.id not in ats_req_games:
                # NOTE: model object is changed locally, but should NOT be saved!
                swami_pick.clear_ats()
            assert game.id not in self.game_pick
            self.game_pick[game.id] = swami_pick.get_pick()

    def get_pick(self, game: Game) -> Pick | None:
        """Return swami's pick for specified game.  For now, this assumes that picks
        have already been loaded into the `swami_pick` table, but later, this call (or
        another utility call) can solicit picks if not already made.

        :param game: game data (actually, only interested in `id`)
        :return: predictions and confidence for both SU and ATS
        """
        if game.id in self.game_pick:
            return self.game_pick[game.id]

        try:
            swami_pick = (SwamiPick
                          .select()
                          .where(SwamiPick.swami_id == self.id,
                                 SwamiPick.game_id == game.id)
                          .order_by(SwamiPick.pick_ts.desc())
                          .get())
        except DoesNotExist:
            return None
        pick = swami_pick.get_pick()
        return pick

#############
# SwamiPick #
#############

class SwamiPick(BaseModel):
    """Represents both current and historical picks for all swami types.  Note that
    a record can specify any or all of the individual pick elements (su, ats, etc.).

    The "confidence" values for the pick can be used by either the swami class or the
    pool framework to determine which games and/or the number of games to submit to a
    weekly sub-pool.  Typically, the minimum number of games (if less than "all") will
    be chosen (in descending confidence order), along with any others at the same level
    as the lowest rank included.  However, a swami subclass may choose to override the
    default logic and select as many games as desired (e.g. with the season sub-pool
    standing in "mind").

    See the docstring for the `Pick` class for a little bit of subtlety (or whatever
    you want to call it) around the workings of--and relationship between--`pt_spread`
    and `pts_margin`.

    TBD (for when human swamis get into the mix): how to aggregate swami picks for a
    game to represent the most recent intent (while preserving the pick history, for
    audit trail), including how to null-out a previous pick value!!!
    """
    swami      = ForeignKeyField(Swami)
    game       = ForeignKeyField(Game)
    su_winner  = ForeignKeyField(Team, column_name='su_winner',
                                 object_id_name='su_winner_code',
                                 backref='su_picks', null=True)
    ats_winner = ForeignKeyField(Team, column_name='ats_winner',
                                 object_id_name='ats_winner_code',
                                 backref='ats_picks', null=True)
    pt_spread  = FloatField(null=True)  # from home team POV (generally !=0.0)
    pts_margin = FloatField(null=True)  # from winner POV (generally >0.0)
    total_pts  = FloatField(null=True)
    su_conf    = FloatField(null=True)  # confidence for `su_winner`
    ats_conf   = FloatField(null=True)  # confidence for `ats_winner`
    pick_ts    = DateTimeField()        # timestamp managed by framework

    def get_pick(self) -> Pick:
        """Return the pure pick information, with context removed.  It is up to
        the caller to reconcile multiple records for the same parent swami and
        game (e.g. different timestamps and/or pick fields represented)
        """
        # this assumes (make that, *requires*) that `SwamiPick` fields are a
        # strict superset of `Pick` fields
        pick_data = (getattr(self, f) for f in Pick._fields)
        return Pick._make(pick_data)

    def clear_ats(self) -> None:
        """Clear out fields representing ATS picks--whether to save the changes is
        up to the caller.

        LATER: we should represent SU and ATS picks for a game in decoupled records,
        so it is easier to submit and manage the selections more easily!!!
        """
        self.ats_winner = None
        self.ats_conf   = None
