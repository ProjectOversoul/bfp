# -*- coding: utf-8 -*-

from peewee import SqliteDatabase, Model

from .core import DataFile

DFLT_DATABASE = 'bfp.sqlite'

#############
# BaseModel #
#############

db = SqliteDatabase(DataFile(DFLT_DATABASE))

class BaseModel(Model):
    class Meta:
        database = db
