#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from ..game import Game
from . import Swami, SwamiRudi1

def main() -> int:
    """Built-in driver to get swami picks for specified game

    Usage: swami.py <swami_name> <game_id>
    """
    if len(sys.argv) != 3:
        raise RuntimeError("Incorrect number of arguments")

    name = sys.argv[1]
    game_id = int(sys.argv[2])

    if name not in globals() or not issubclass(globals()[name], Swami):
        raise RuntimeError(f"Invalid swami '{name}' specified")
    swami = globals()[name]()

    game = Game.get_by_id(game_id)
    team, margin = swami.pick_winner(game.get_info())
    info = game.get_info()
    results = game.get_results()

    print(f"Game Info: \n{info}")
    print(f"\nPick: {team} by {margin}")
    print(f"\nGame Results: \n{results}")

    outcome = ("wrong", "right")
    print(f"\nYou were {outcome[int(team == results.winner)]}!")

    return 0

if __name__ == '__main__':
    sys.exit(main())
