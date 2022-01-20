# -*- coding: utf-8 -*-

import sys

import regex as re
from peewee import OperationalError

from .utils import parse_argv
from .db_core import db, BaseModel
from .team import Team
from .game import Game
from .swami import Swami, SwamiPick

##########
# Schema #
##########

def create_schema(models: list[BaseModel | str] | str, force=False) -> int:
    """Create tables for specified models.  Note that this does nothing if the underlying
    tables already exist, even if the model schema has changed.

    :raises RuntimeError: if valid models are specified

    :param models: list of model objects or names, or string of comma-separated names
    :return: status code (0 is success)
    """
    if isinstance(models, str):
        models = models.split(',')
    if isinstance(models[0], str):
        models_new = []
        for model in models:
            if model not in globals():
                raise RuntimeError(f"Model {model} not imported")
            model_obj = globals()[model]
            if not issubclass(model_obj, BaseModel):
                raise RuntimeError(f"Model {model} must be subclass of `BaseModel`")
            models_new.append(model_obj)
        models = models_new

    if db.is_closed():
        db.connect()
    for model in models:
        try:
            model.create_table(safe=False)
        except OperationalError as e:
            if re.fullmatch(r'table "(\w+)" already exists', str(e)) and force:
                model.drop_table(safe=False)
                model.create_table(safe=False)
            else:
                raise

    return 0

########
# Main #
########

def main() -> int:
    """Built-in driver to invoke various utility functions for the module

    Usage: db_admin.py <util_func> [<args> ...]

    Functions/usage:
      - create_schema models=<model,model,...> [force=<bool>]
    """
    if len(sys.argv) < 2:
        print(f"Utility function not specified", file=sys.stderr)
        return -1
    elif sys.argv[1] not in globals():
        print(f"Unknown utility function '{sys.argv[1]}'", file=sys.stderr)
        return -1

    util_func = globals()[sys.argv[1]]
    args, kwargs = parse_argv(sys.argv[2:])

    return util_func(*args, **kwargs)

if __name__ == '__main__':
    sys.exit(main())
