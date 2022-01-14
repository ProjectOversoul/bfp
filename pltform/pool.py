#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from os import environ
from typing import Any, TextIO
from collections.abc import Iterable
from collections import Counter
from itertools import groupby
from enum import Enum

from peewee import query_to_string

from .utils import parse_argv
from .core import cfg, log, LogicError
from .game import Game, Pick, PLAYOFF_WEEKS, WeekStr
from .swami import Swami

POOL_CONFIG = environ.get('BFP_POOL_CONFIG') or 'pools.yml'
cfg.load(POOL_CONFIG)

#########
# Score #
#########

class Score(Counter):
    """This represents the scoring of picks within a pool, run (e.g. season), week,
    or individual game (and not football-level scores).  Emulates a list that looks
    like `[wins, losses, ties]`, except it does some tabulation for us.
    """
    @staticmethod
    def init_scores() -> list['Score']:
        return [Score.empty(), Score.empty()]

    @staticmethod
    def empty() -> 'Score':
        return Score(0, 0, 0)

    def __init__(self, wins: int, losses: int, ties: int):
        super().__init__({0: wins, 1: losses, 2: ties})

    def is_empty(self):
        return self.total() == 0

# some useful type aliases
Swamis        = list[Swami]
Scores        = list[Score]       # [su_score, ats_score]
GamePick      = dict[Game, Pick]
SwamiPick     = dict[Swami, Pick]
SwamiGamePick = dict[Swami, GamePick]
WeekScores    = dict[int, Scores]
SwamiScores   = dict[Swami, Scores]

def compute_scores(game: Game, pick: Pick) -> Scores:
    """Return SU and ATS score tuples for an individual  pick against a game
    (all values will be 1 or 0).  Empty `Score` is returned for any game not
    yet played or portion of the pick not made (e.g. no ATS pick).
    """
    if not game.winner:
        return [Score.empty(), Score.empty()]

    su_win   = not game.is_tie and pick.su_winner == game.winner
    su_loss  = not game.is_tie and pick.su_winner != game.winner
    su_tie   = game.is_tie
    su_score = Score(int(su_win), int(su_loss), int(su_tie))
    if game.pt_spread and pick.ats_winner:
        # `not game.ats_winner` indicates a push
        ats_win   = game.ats_winner and pick.ats_winner == game.ats_winner
        ats_loss  = game.ats_winner and pick.ats_winner != game.ats_winner
        ats_tie   = not game.ats_winner
        ats_score = Score(int(ats_win), int(ats_loss), int(ats_tie))
    else:
        ats_score = Score.empty()

    return [su_score, ats_score]

###########
# PoolRun #
###########

# used in reporting
SWAMI_COL = "Swami"
TOTAL_COL = "Total"
WIN_PCT   = "Win %"

class PoolSeg(Enum):
    SU  = 0
    ATS = 1

def PoolSegStr(pool_seg: PoolSeg) -> str:
    return {PoolSeg.SU:  "Straight Up",
            PoolSeg.ATS: "Against the Spread"}[pool_seg]

class PoolRun:
    """Run a pool for a specified timeframe (i.e. complete or partial season)
    """
    swamis:       list[Swami]
    season:       int
    weeks:        list[int] | None
    week_games:   dict[int, list[Game]]
    game_picks:   dict[Game, SwamiPick]
    week_picks:   dict[int, SwamiGamePick]
    week_scores:  dict[int, SwamiScores]
    swami_scores: dict[Swami, WeekScores]
    tot_scores:   SwamiScores

    def __init__(self, swamis: Iterable[Swami], season: int, weeks: Iterable[int] = None):
        """Run pool for the specified season, optionally narrowed to specific
        weeks within the season.  Note that special values for playoff weeks
        are defined using the `game.PlayoffWeek` enum, and `game.PLAYOFF_WEEKS`
        may be used to represent the set of all playoff weeks.
        """
        if weeks is not None:
            weeks = list(weeks)
        self.swamis       = list(swamis)
        self.season       = season
        self.weeks        = weeks
        self.week_games   = {}
        self.game_picks   = {}
        self.week_picks   = {}
        self.week_scores  = {}
        self.swami_scores = {}
        self.tot_scores   = {}

    def get_winners(self) -> tuple[Swamis, Swamis | None]:
        """Not a pretty way to do this, but oh well...
        """
        if not self.tot_scores:
            raise LogicError("Results yet not computed")
        by_su = sorted(self.tot_scores.items(), key=lambda s: -s[1][0][0])
        by_ats = sorted(self.tot_scores.items(), key=lambda s: -s[1][1][0])
        su_wins, su_scores = next(groupby(by_su, key=lambda s: s[1][0][0]))
        ats_wins, ats_scores = next(groupby(by_ats, key=lambda s: s[1][1][0]))
        su_winner = [s[0] for s in su_scores]
        ats_winner = [s[0] for s in ats_scores] if ats_wins > 0 else [None]
        return su_winner, ats_winner

    def run(self) -> None:
        """Tabulate picks for the season from the competing swamis, and compute
        results against the actual game outcomes.

        Sample code for sorting/use the run results:
            run = pool.get_run(2021)
            run.run()

            # find week 1 SU winner
            week_1 = run.week_scores[1]
            week_1_by_su = sorted(week_1.items(), key=lambda s: -s[1][0][0])
            week_1_su_winner = next(iter(week_1_by_su))[0]

            # find season (2021) ATS winner
            season = run.tot_scores
            season_by_ats = sorted(season.items(), key=lambda s: -s[1][1][0])
            season_ats_winner = next(iter(season_by_ats))[0]
        """
        query = Game.select().where(Game.season == self.season)
        if self.weeks:
            query = query.where(Game.week << self.weeks)
        query = query.order_by(Game.season, Game.week, Game.datetime)

        log.debug("Pool games SQL: " + query_to_string(query))
        games = query.execute()

        # note, could use `itertools.groupby` on week
        for game in games:
            week = game.week
            if week not in self.week_games:
                self.week_games[week] = []
            self.week_games[week].append(game)
            self.game_picks[game] = {}
            if week not in self.week_picks:
                self.week_picks[week] = {}
            for swami in self.swamis:
                log.debug(f"Picks for week {week}, game {game.matchup}, swami {swami}")
                pick = swami.get_pick(game.get_info())
                if swami not in self.week_picks[week]:
                    self.week_picks[week][swami] = {}
                self.game_picks[game][swami] = pick
                self.week_picks[week][swami][game] = pick

        if not self.game_picks:
            raise RuntimeError("No games selected")
        self.compute_results()

    def compute_results(self) -> None:
        """Uses the data in `self.game_picks` and the actual game results to
        populate the following variables:
          `self.week_scores`  - used to determine weekly winners
          `self.tot_scores`   - used to determine season winners
          `self.swami_scores` - used for `print_results()`

        Note that the results are not sorted within these fields; it is up to
        the caller to sort, see `run()` for examples
        """
        for game, swami_picks in self.game_picks.items():
            week = game.week
            if week not in self.week_scores:
                self.week_scores[week] = {}
            for swami, pick in swami_picks.items():
                scores = compute_scores(game, pick)
                if swami not in self.week_scores[week]:
                    self.week_scores[week][swami] = Score.init_scores()
                if swami not in self.swami_scores:
                    self.swami_scores[swami] = {}
                if week not in self.swami_scores[swami]:
                    self.swami_scores[swami][week] = Score.init_scores()
                if swami not in self.tot_scores:
                    self.tot_scores[swami] = Score.init_scores()
                self.swami_scores[swami][week][0] += scores[0]
                self.week_scores[week][swami][0] += scores[0]
                self.tot_scores[swami][0] += scores[0]
                if not scores[1].is_empty:
                    self.swami_scores[swami][week][1] += scores[1]
                    self.week_scores[week][swami][1] += scores[1]
                    self.tot_scores[swami][1] += scores[1]

    def print_results(self, pool_seg: PoolSeg, file: TextIO = None) -> None:
        """Print season summary and weekly picks by swami for the specified
        pool "segment" (i.e. SU vs. ATS).
        """
        winners = self.get_winners()
        su_winners = ', '.join(str(w) for w in winners[0])
        ats_winners = ', '.join(str(w) for w in winners[1])
        print("Winners:", file=file)
        print("SU\t{su_winners}", file=file)
        print("ATS\t{ats_winners}", file=file)

        title = f"Season Summary ({PoolSegStr(pool_seg)})"
        print(f"\n{title}\n{'-' * len(title)}")
        header = self.season_report_hdr()
        print("\t".join(header), file=file)
        for report_data in self.season_report_iter(pool_seg):
            iter_data = (str(report_data.get(key)) for key in header)
            print("\t".join(iter_data), file=file)

        for week in self.week_scores:
            subtitle = f"{WeekStr(week)} ({PoolSegStr(pool_seg)})"
            print(f"\n{subtitle}\n{len(subtitle) * '-'}")
            header = self.week_report_hdr(week)
            print("\t".join(header), file=file)
            for report_data in self.week_report_iter(week, pool_seg):
                iter_data = (str(report_data.get(key)) for key in header)
                print("\t".join(iter_data), file=file)

    def print_results_md(self, pool_seg: PoolSeg, file: TextIO = None) -> None:
        """Same as `print_results()` except in markdown format
        """
        winners = self.get_winners()
        su_winners = ', '.join(str(w) for w in winners[0])
        ats_winners = ', '.join(str(w) for w in winners[1])
        print("\n## Winners ##")
        print("| Segment | Winner(s) |", file=file)
        print("| --- | --- |", file=file)
        print(f"| SU | {su_winners} |", file=file)
        print(f"| ATS | {ats_winners} |", file=file)

        print(f"\n## Season Summary ({PoolSegStr(pool_seg)}) ##")
        header = self.season_report_hdr()
        print("| ", " | ".join(header), " |", file=file)
        print("| ", " --- |" * len(header), file=file)
        for report_data in self.season_report_iter(pool_seg):
            iter_data = (str(report_data.get(key)) for key in header)
            print("| ", " | ".join(iter_data), " |", file=file)

        for week in self.week_scores:
            print(f"\n### {WeekStr(week)}  ({PoolSegStr(pool_seg)}) ###")
            header = self.week_report_hdr(week)
            print("| ", " | ".join(header), " |", file=file)
            print("| ", " --- |" * len(header), file=file)
            for report_data in self.week_report_iter(week, pool_seg):
                iter_data = (str(report_data.get(key)) for key in header)
                print("| ", " | ".join(iter_data), " |", file=file)

    def season_report_hdr(self) -> list[str]:
        """Header field names for the Season Report, which represent the keys for
        the data returned by `season_report_iter()`.
        """
        week_names = [WeekStr(w) for w in self.week_scores]
        return [SWAMI_COL] + week_names + [TOTAL_COL, WIN_PCT]

    def season_report_iter(self, pool_seg: PoolSeg) -> dict[str, int]:
        """The Season Report shows the weekly results for each swami across all of
        the weeks in the pool run.
        """
        score_idx = pool_seg.value
        by_su = sorted(self.tot_scores.items(), key=lambda s: -s[1][0][0])
        for swami, tot_score in by_su:
            week_scores = self.swami_scores[swami]
            wins = {WeekStr(w): s[score_idx][0] for w, s in week_scores.items()}
            tot_wins = self.tot_scores[swami][score_idx][0]
            tot_ties = self.tot_scores[swami][score_idx][2]
            tot_picks = self.tot_scores[swami][score_idx].total()
            win_pct = f"{(tot_wins + tot_ties / 2.0) / tot_picks * 100.0:.0f}%"
            yield {SWAMI_COL: swami.name} | wins | {TOTAL_COL: tot_wins, WIN_PCT: win_pct}

    def week_report_hdr(self, week: int) -> list[str]:
        """Header field names for the Week Report, which represent the keys for
        the data returned by `season_report_iter()`.
        """
        matchups = [g.matchup for g in self.week_games[week]]
        return [SWAMI_COL] + matchups

    def week_report_iter(self, week: int, pool_seg: PoolSeg) -> dict[str, int]:
        """The Week Report shows all of the individual picks for each game by
        all of the swamis in the pool.
        """
        if pool_seg != PoolSeg.SU:
            raise ImplementationError(f"Segment {pool_seg} not yet implemented")
        winner_row = {g.matchup: (g.winner if not g.is_tie else "-tie-") if g.winner else '-tbd-'
                      for g in self.week_games[week]}
        yield {SWAMI_COL: "Winner"} | winner_row
        winners = set(g.winner for g in self.week_games[week] if not g.is_tie)
        winning_picks = Counter()
        for swami, game_picks in self.week_picks[week].items():
            picks = {}
            for g, p in game_picks.items():
                win_ind = '*' if p.su_winner in winners else ''
                picks[g.matchup] = p.su_winner.code + win_ind
                winning_picks[g.matchup] += int(bool(win_ind))
            yield {SWAMI_COL: swami.name} | picks
        nswamis = len(self.week_picks[week])
        pick_pct = {key: f"{wins / nswamis * 100.0:.0f}%"
                    for key, wins in winning_picks.items()}
        yield {SWAMI_COL: WIN_PCT} | pick_pct

##############
# PoolResult #
##############

class PoolResult:
    """Not sure what this is yet, perhaps history of results by season (i.e. run).
    Will probably need to think about the appropriate persistence mechanism for
    this, whether database or pickle/shelve.
    """
    pass

########
# Pool #
########

class Pool:
    """Pool on game predictions between swamis
    """
    name:   str
    swamis: dict[str, Swami]  # indexed by name (do we need to do this???)
    runs:   list[PoolRun]

    def __init__(self, name: str, **kwargs: Any):
        """Note that the swamis for this pool are generally specified in the
        config file entry, but may be overridden in `kwargs`
        """
        pools = cfg.config('pools')
        if name not in pools:
            raise RuntimeError(f"Pool '{name}' is not known")
        pool_info = pools[name]
        # if `swamis` specified in `kwargs`, replaces config file list (no merging)
        swamis = kwargs.pop('swamis', None) or pool_info.get('swamis')

        self.name   = name
        self.swamis = {}
        self.runs   = []
        # idx is used below as a count of the inbound swamis
        for idx, swami in enumerate(swamis):
            if isinstance(swami, str):
                swami = Swami.new(swami)
            self.swamis[swami.name] = swami
        if len(self.swamis) < 1:
            raise RuntimeError("At least one swami must be specified")
        if len(self.swamis) < idx + 1:
            raise RuntimeError("Swami names must be unique")

    def get_run(self, season: int, weeks: Iterable[int] = None) -> PoolRun:
        """Initializes and returns the pool run instance; it is up to the caller
        to actually run it.
        """
        run = PoolRun(self.swamis.values(), season, weeks)
        self.runs.append(run)

        return run

    def print_swami_bios_md(self, file: TextIO = None) -> None:
        print("\n## Swami Bios ##", file=file)
        print("| Name | About |", file=file)
        print("| --- | --- |", file=file)
        for name, swami in self.swamis.items():
            print(f"| {name} | {swami.about_me} |", file=file)

########
# Main #
########

def main() -> int:
    """Built-in driver to run a pool for a specified timeframe--that is,
    a full or partial season.

    Later, if/when we are persisting pool results, we will need to revamp
    this to be the overall pool manager interface (or create a new script/
    app to do so).

    Usage: pool.py <pool_name> <season> [<weeks>]

    where <weeks> may be specified as:
      - single week    (e.g. '17')
      - list of weeks  (e.g. '6,7,8,9')
      - range of weeks (e.g. '9-17')
      - special values: 'playoffs', etc.
    """
    if len(sys.argv) not in (3, 4):
        raise RuntimeError("Incorrect number of arguments")

    name = sys.argv[1]
    season = int(sys.argv[2])
    args, kwargs = parse_argv(sys.argv[3:])
    if len(args) > 1 or kwargs:
        raise RuntimeError("Incorrect number of arguments, or bad value")

    if args:
        # special parsing for <weeks> arg, and convert to list
        weeks = args[0]
        if isinstance(weeks, str):
            if weeks == 'playoffs':
                weeks = PLAYOFF_WEEKS
            elif ',' in weeks:
                weeks = [int(x) for x in weeks.split(',')]
            elif '-' in weeks:
                start, end = weeks.split('-', 1)
                weeks = range(int(start), int(end) + 1)
            else:
                weeks = [int(weeks)]
        else:
            weeks = [weeks]
    else:
        weeks = None

    pool = Pool(name)
    run = pool.get_run(season, weeks)
    run.run()
    run.print_results_md(PoolSeg.SU)
    pool.print_swami_bios_md()

    return 0

if __name__ == '__main__':
    sys.exit(main())
