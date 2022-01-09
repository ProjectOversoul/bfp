#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .base_model import BaseModel

########
# Team #
########

class Team(BaseModel):
    """Represents a currently active team; note that data for prior incarnations
    of teams (e.g. Decatur Staleys or Oakland Raiders) are incorporated into the
    descendent specified by https://www.pro-football-reference.com/teams (whether
    or not one agrees, cf. Browns->Ravens)
    """
    code      = TextField(primary_key=True)
    name      = TextField()
    full_name = TextField()
    conf      = TextField()
    div       = TextField()
    pfr_code  = TextField()
    timezone  = TextField(null=True)

    @classmethod
    def load_base_data(cls) -> None:
        pass

########
# Main #
########

def main() -> int:
    pass

if __name__ == '__main__':
    sys.exit(main())
