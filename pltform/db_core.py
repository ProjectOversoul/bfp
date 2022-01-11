# -*- coding: utf-8 -*-

from peewee import SqliteDatabase, Model

from .core import cfg, DataFile, ConfigError

DFLT_DB    = 'bfp.db'
DB_KEY     = 'databases'
SQLITE_KEY = 'sqlite'

db_config = cfg.config(DB_KEY)
if not db_config or SQLITE_KEY not in db_config:
    raise ConfigError("'{DB_KEY}' or '{SQLITE_KEY}' not found in config file")
SQLITE = db_config.get(SQLITE_KEY)

#############
# BaseModel #
#############

pragmas = {'journal_mode'            : 'wal',
           'cache_size'              : -1 * 64000,  # 64MB
           'foreign_keys'            : 1,
           'ignore_check_constraints': 0,
           'synchronous'             : 0}

db_file = SQLITE.get('db_file') or DFLT_DB
db = SqliteDatabase(DataFile(db_file), pragmas)

class BaseModel(Model):
    class Meta:
        database = db
