# -*- coding: utf-8 -*-

from os import environ, rename
import os.path
from datetime import datetime
import logging
import logging.handlers

from . import utils

######################
# Config/Environment #
######################

FILE_DIR     = os.path.dirname(os.path.realpath(__file__))
BASE_DIR     = os.path.realpath(os.path.join(FILE_DIR, os.pardir))

CONFIG_DIR   = 'config'
DFLT_CONFIG  = ['config.yml']
CONFIG_FILES = environ.get('BPF_CONFIG_FILES') or DFLT_CONFIG
cfg          = utils.Config(CONFIG_FILES, os.path.join(BASE_DIR, CONFIG_DIR))

DEBUG        = int(environ.get('BPF_DEBUG') or 0)

########
# Data #
########

DATA_DIR      = 'data'
ARCH_DT_FMT   = '%Y%m%d_%H%M%S'

def DataFile(file_name: str, dir: str = DATA_DIR) -> str:
    """Given name of file, return full path name (in DATA_DIR, or specified
    directory)
    """
    return os.path.join(BASE_DIR, dir, file_name)

def ArchiveDataFile(file_name: str) -> None:
    """Rename data file to "archived" version (current datetime appended),
    which also has the effect of removing it from the file system, so that
    a new version can be created
    """
    data_file = DataFile(file_name)
    arch_dt = datetime.now().strftime(ARCH_DT_FMT)
    try:
        rename(data_file, data_file + '-' + arch_dt)
    except FileNotFoundError:
        pass

###########
# Logging #
###########

# create logger (TODO: logging parameters belong in config file as well!!!)
LOGGER_NAME  = environ.get('BPF_LOG_NAME') or 'bpf'
LOG_DIR      = 'log'
LOG_FILE     = LOGGER_NAME + '.log'
LOG_PATH     = os.path.join(BASE_DIR, LOG_DIR, LOG_FILE)
LOG_FMTR     = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)s]: %(message)s')
LOG_FILE_MAX = 25000000
LOG_FILE_NUM = 50

dflt_hand = logging.handlers.RotatingFileHandler(LOG_PATH, 'a', LOG_FILE_MAX, LOG_FILE_NUM)
dflt_hand.setLevel(logging.DEBUG)
dflt_hand.setFormatter(LOG_FMTR)

dbg_hand = logging.StreamHandler()
dbg_hand.setLevel(logging.DEBUG)
dbg_hand.setFormatter(LOG_FMTR)

log = logging.getLogger(LOGGER_NAME)
log.setLevel(logging.INFO)
log.addHandler(dflt_hand)
if DEBUG:
    log.setLevel(logging.DEBUG)
    if DEBUG > 1:
        log.addHandler(dbg_hand)

##############
# Exceptions #
##############

class DataError(RuntimeError):
    """Thrown if there is a problem with any of the data at runtime, whether
    due to bad external data or errrant internal processing
    """
    pass

class ConfigError(RuntimeError):
    """Thrown if there is a problem with a config file entry, or combination
    of entries
    """
    pass

class LogicError(RuntimeError):
    """Basically the same as an assert, but with a `raise` interface
    """
    pass

class ImplementationError(RuntimeError):
    """Thrown if there is a problem implementing an internal interface (e.g.
    `Swami` subclass)
    """
    pass
