#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from ..game import Game
from . import Swami

def main() -> int:
    """Built-in driver to get swami picks for specified game

    Usage: swami.py <swami_name> <game_id>
    """
    if len(sys.argv) != 3:
        raise RuntimeError("Incorrect number of arguments")

    name = sys.argv[1]
    game_id = int(sys.argv[2])

    swami = Swami.new(name)
    game = Game.get_by_id(game_id)
    team, _, margin, total = swami.get_pick(game.get_info())
    info = game.get_info()
    results = game.get_results()

    print(f"{info}")
    print(f"\nYour pick: {team} by {margin}")
    print(f"\n{results}")

    outcome = ("wrong", "right")
    print(f"\nYou were {outcome[int(team == results.winner)]}!")

    return 0

if __name__ == '__main__':
    sys.exit(main())
