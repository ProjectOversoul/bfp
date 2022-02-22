#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from os import environ
from typing import TextIO
from collections.abc import Iterable, Iterator
from collections import Counter
from itertools import groupby
from operator import attrgetter
from enum import Enum

from peewee import query_to_string

from .utils import parse_argv
from .core import cfg, log, LogicError, ImplementationError
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
Scores        = list[Score]       # [su_score, ats_score]
GamePick      = dict[Game, Pick]
WeekScores    = dict[int, Scores]

def compute_scores(game: Game, pick: Pick) -> Scores:
    """Return SU and ATS score tuples for an individual  pick against a game
    (all values will be 1 or 0).  Empty `Score` is returned for any game not
    yet played or portion of the pick not made (e.g. no ATS pick).
    """
    if not game.winner:
        return [Score.empty(), Score.empty()]

    # Pick has to have a non-zero `pts_margin` in order to get credit for a
    # win, otherwise it is chalked up as a loss (unless the game is tied, in
    # which case the pick is deemed a push); see LOL in fte.py for rationale.
    # PERHAPS we should REVISIT, and give "win" credit for a zero-margin pick
    # that ends in a game tie (wonder if that has ever happened in history)!!!
    su_win   = not game.is_tie and pick.su_winner == game.winner and pick.pts_margin > 0
    su_loss  = not game.is_tie and (pick.su_winner != game.winner or pick.pts_margin == 0)
    su_tie   = game.is_tie
    su_score = Score(int(su_win), int(su_loss), int(su_tie))
    if game.pt_spread and pick.ats_winner:
        # `game.ats_winner is None` indicates a push
        ats_win   = game.ats_winner is not None and pick.ats_winner == game.ats_winner
        ats_loss  = game.ats_winner is not None and pick.ats_winner != game.ats_winner
        ats_tie   = not game.ats_winner
        ats_score = Score(int(ats_win), int(ats_loss), int(ats_tie))
    else:
        ats_score = Score.empty()

    return [su_score, ats_score]

###########
# SubPool #
###########

# used in reporting
SWAMI_COL = "Swami"
TOTAL_COL = "Total"
WIN_PCT   = "Win %"

class ReportFmt(Enum):
    TXT  = 0
    MD   = 1
    HTML = 2

class SubPoolType(Enum):
    SU      = 0
    ATS     = 1
    PLAYOFF = 2  # note, not a valid score index value

def SubPoolStr(sp_type: SubPoolType) -> str:
    return {SubPoolType.SU:      "Straight Up",
            SubPoolType.ATS:     "Against the Spread",
            SubPoolType.PLAYOFF: "Playoff"}[sp_type]

class SubPool:
    """Reporting class for sub-pool type: SU, ATS, or PLAYOFF
    """
    pool:    'Pool'
    sp_type: SubPoolType

    @classmethod
    def get_class(cls, sp_type: SubPoolType) -> type:
        if sp_type not in SUB_POOL_MAP:
            raise LogicError(f"Unknown SubPoolType '{str(sp_type)}'")
        sp_class = SUB_POOL_MAP[sp_type]
        assert issubclass(sp_class, cls)
        return sp_class

    def __new__(cls, parent_pool: 'Pool', sp_type: SubPoolType):
        sp_class = cls.get_class(sp_type)
        return super().__new__(sp_class)

    def __init__(self, parent_pool: 'Pool', sp_type: SubPoolType):
        self.pool = parent_pool
        self.sp_type = sp_type

    def week_iter(self) -> Iterator[int]:
        return (w for w in self.pool.week_scores)

    def swami_scores_iter(self, swami: Swami) -> Iterator[tuple[int, Scores]]:
        week_scores = self.pool.swami_scores[swami]
        return (ws for ws in week_scores.items())

    def get_winner(self) -> list[Swami]:
        """Not a pretty way to do this, but oh well...(only works for SU or ATS)

        TODO/FIX: this isn't right for ATS (or actually any sub-pool where not all
        games are mandatory picks)--could change ths to always use win percentage
        for determination, though we may still want to represent number of wins in
        reporting (especially when all game picks are required)!!!

        Note that we always return a list of `Swami`s, even in the case of single
        winners, to keep the interface simpler; it is up to the caller (typically
        some output/reporting mechanism) to "un-list" it in rendering.
        """
        pool = self.pool
        if not pool.tot_scores:
            raise LogicError("Results yet not computed")
        score_idx = self.sp_type.value
        by_wins = sorted(pool.tot_scores.items(), key=lambda s: -s[1][score_idx][0])
        wins, scores = next(groupby(by_wins, key=lambda s: s[1][score_idx][0]))
        winner = [s[0] for s in scores] if wins > 0 else [None]
        return winner

    def print_results(self, file: TextIO = None) -> None:
        """Print sub-pool summary and individual picks, by swami
        """
        pool = self.pool
        winner = self.get_winner()
        plural = 's' if len(winner) > 1 else ''
        winner_str = ', '.join(str(w) for w in winner)
        print(f"Winner{plural} ({SubPoolStr(self.sp_type)}):", file=file)
        print(winner_str, file=file)

        title = f"Season Summary ({SubPoolStr(self.sp_type)})"
        print(f"\n{title}\n{'-' * len(title)}")
        header = self.season_report_hdr()
        print("\t".join(header), file=file)
        for report_data in self.season_report_iter():
            iter_data = (str(report_data.get(key)) for key in header)
            print("\t".join(iter_data), file=file)

        for week in self.week_iter():
            subtitle = f"{WeekStr(week)} ({SubPoolStr(self.sp_type)})"
            print(f"\n{subtitle}\n{len(subtitle) * '-'}")
            header = self.week_report_hdr(week)
            print("\t".join(header), file=file)
            for report_data in self.week_report_iter(week):
                iter_data = (str(report_data.get(key, '')) for key in header)
                print("\t".join(iter_data), file=file)

    def print_results_md(self, file: TextIO = None) -> None:
        """Same as `print_results()` except in markdown format
        """
        pool = self.pool
        winner = self.get_winner()
        plural = 's' if len(winner) > 1 else ''
        winner_str = ', '.join(str(w) for w in winner)
        print(f"\n## Winner{plural} ({SubPoolStr(self.sp_type)}) ##", file=file)
        print(winner_str, file=file)

        print(f"\n## Season Summary ({SubPoolStr(self.sp_type)}) ##")
        header = self.season_report_hdr()
        print("| ", " | ".join(header), " |", file=file)
        print("| ", " --- |" * len(header), file=file)
        for report_data in self.season_report_iter():
            iter_data = (str(report_data.get(key)) for key in header)
            print("| ", " | ".join(iter_data), " |", file=file)

        for week in self.week_iter():
            print(f"\n### {WeekStr(week)} ({SubPoolStr(self.sp_type)}) ###")
            header = self.week_report_hdr(week)
            print("| ", " | ".join(header), " |", file=file)
            print("| ", " --- |" * len(header), file=file)
            for report_data in self.week_report_iter(week):
                iter_data = (str(report_data.get(key, '')) for key in header)
                print("| ", " | ".join(iter_data), " |", file=file)

    def season_report_hdr(self) -> list[str]:
        """Header field names for the Season Report, which represent the keys for
        the data returned by `season_report_iter()`.
        """
        pool = self.pool
        week_names = [WeekStr(w) for w in self.week_iter()]
        return [SWAMI_COL] + week_names + [TOTAL_COL, WIN_PCT]

    def season_report_iter(self) -> dict[str, int]:
        """The Season Report shows the weekly results for each swami across all of
        the weeks in the pool run.
        """
        pool = self.pool
        score_idx = self.sp_type.value
        by_wins = sorted(pool.tot_scores.items(), key=lambda s: -s[1][score_idx][0])
        for swami, tot_score in by_wins:
            wins = {WeekStr(w): s[score_idx][0] for w, s in self.swami_scores_iter(swami)}
            tot_wins = pool.tot_scores[swami][score_idx][0]
            tot_ties = pool.tot_scores[swami][score_idx][2]
            tot_picks = pool.tot_scores[swami][score_idx].total() or -1
            win_pct = f"{(tot_wins + tot_ties / 2.0) / tot_picks * 100.0:.0f}%"
            yield {SWAMI_COL: swami.name} | wins | {TOTAL_COL: tot_wins, WIN_PCT: win_pct}

    def week_report_hdr(self, week: int) -> list[str]:
        """Header field names for the Week Report, which represent the keys for
        the data returned by `season_report_iter()`.
        """
        pool = self.pool
        matchups = [g.matchup for g in pool.week_games[week]]
        return [SWAMI_COL] + matchups + [TOTAL_COL, WIN_PCT]

    def week_report_iter(self, week: int) -> dict[str, int]:
        raise ImplementationError("Must be implemented by subclasses")

class SubPoolSU(SubPool):
    def week_iter(self) -> Iterator[int]:
        return (w for w in self.pool.week_scores if w < 100)

    def week_scores_iter(self) -> Iterator[tuple[int, Scores]]:
        return (ws for ws in self.pool.week_scores if ws[0] < 100)

    def swami_scores_iter(self, swami: Swami) -> Iterator[tuple[int, Scores]]:
        week_scores = self.pool.swami_scores[swami]
        return (ws for ws in week_scores.items() if ws[0] < 100)

    def week_report_iter(self, week: int) -> dict[str, int]:
        """The Week Report shows all of the individual picks for each game by all
        of the swamis in the pool.
        """
        pool = self.pool
        # extra verbosity here for consistency with ATS code below
        winner_row = {g.matchup: g.winner if g.winner and not g.is_tie
                      else ("-tie-" if g.is_tie else "-tbd-")
                      for g in pool.week_games[week]}
        yield {SWAMI_COL: "Winner"} | winner_row | {TOTAL_COL: '', WIN_PCT: ''}

        winners = set(g.winner for g in pool.week_games[week] if not g.is_tie)
        total_picks = Counter()
        winning_picks = Counter()
        results = []
        for swami, game_picks in pool.week_picks[week].items():
            picks = {}
            swami_wins  = 0
            swami_ties  = 0
            swami_total = 0
            for g, p in game_picks.items():
                if not p.su_winner:
                    continue
                win_ind = ''
                swami_total += 1
                total_picks[g.matchup] += 1
                if p.su_winner in winners:
                    win_ind = '*'
                    swami_wins += 1
                    winning_picks[g.matchup] += 1
                elif g.is_tie:
                    swami_ties += 1
                picks[g.matchup] = p.su_winner.code + win_ind
            win_pct = f"{(swami_wins + swami_ties / 2.0) / (swami_total or -1) * 100.0:.0f}%"
            result = {SWAMI_COL: swami.name} | picks | {TOTAL_COL: swami_wins, WIN_PCT: win_pct}
            results.append(result)
        for x in sorted(results, key=lambda r: r[WIN_PCT], reverse=True):
            yield x

        pick_pct = {key: f"{wins / total_picks[key] * 100.0:.0f}%"
                    for key, wins in winning_picks.items()}
        yield {SWAMI_COL: WIN_PCT} | pick_pct | {TOTAL_COL: '', WIN_PCT: ''}

class SubPoolATS(SubPool):
    def week_iter(self) -> Iterator[int]:
        return (w for w in self.pool.week_scores if w < 100)

    def week_scores_iter(self) -> Iterator[int]:
        return (ws for ws in self.pool.week_scores if ws[0] < 100)

    def swami_scores_iter(self, swami: Swami) -> Iterator[tuple[int, Scores]]:
        week_scores = self.pool.swami_scores[swami]
        return (ws for ws in week_scores.items() if ws[0] < 100)

    def week_report_iter(self, week: int) -> dict[str, int]:
        """The Week Report shows all of the individual picks for each game by all
        of the swamis in the pool.
        """
        pool = self.pool
        winner_row = {g.matchup: g.ats_winner if g.ats_winner
                      else ("-push-" if g.is_ats_push else "-n/a-")
                      for g in pool.week_games[week]}
        yield {SWAMI_COL: "Winner"} | winner_row | {TOTAL_COL: '', WIN_PCT: ''}
        winners = set(g.ats_winner for g in pool.week_games[week] if g.ats_winner)
        total_picks = Counter()
        winning_picks = Counter()
        results = []
        for swami, game_picks in pool.week_picks[week].items():
            picks = {}
            swami_wins  = 0
            swami_ties  = 0
            swami_total = 0
            for g, p in game_picks.items():
                if not p.ats_winner:
                    continue
                win_ind = ''
                swami_total += 1
                total_picks[g.matchup] += 1
                if p.ats_winner in winners:
                    win_ind = '*'
                    swami_wins += 1
                    winning_picks[g.matchup] += 1
                elif g.is_ats_push:
                    swami_ties += 1
                picks[g.matchup] = p.ats_winner.code + win_ind
            win_pct = f"{(swami_wins + swami_ties / 2.0) / (swami_total or -1) * 100.0:.0f}%"
            result = {SWAMI_COL: swami.name} | picks | {TOTAL_COL: swami_wins, WIN_PCT: win_pct}
            results.append(result)
        for x in sorted(results, key=lambda r: r[WIN_PCT], reverse=True):
            yield x

        pick_pct = {key: f"{wins / total_picks[key] * 100.0:.0f}%"
                    for key, wins in winning_picks.items()}
        yield {SWAMI_COL: WIN_PCT} | pick_pct | {TOTAL_COL: '', WIN_PCT: ''}

class SubPoolPlayoff(SubPool):
    def week_iter(self) -> Iterator[int]:
        return (w for w in self.pool.week_scores if w >= 100)

    def week_scores_iter(self) -> Iterator[int]:
        return (ws for ws in self.pool.week_scores if ws[0] >= 100)

    def swami_scores_iter(self, swami: Swami) -> Iterator[tuple[int, Scores]]:
        week_scores = self.pool.swami_scores[swami]
        return (ws for ws in week_scores.items() if ws[0] >= 100)

    def get_winner(self) -> list[Swami]:
        raise ImplementationError("Not yet implemented")

    def print_results(self, file: TextIO = None) -> None:
        raise ImplementationError("Not yet implemented")

    def print_results_md(self, file: TextIO = None) -> None:
        raise ImplementationError("Not yet implemented")

SUB_POOL_MAP = {SubPoolType.SU:      SubPoolSU,
                SubPoolType.ATS:     SubPoolATS,
                SubPoolType.PLAYOFF: SubPoolPlayoff}

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
    name:         str
    season:       int
    swamis:       dict[str, Swami]  # indexed by name (do we need to do this???)
    sub_pools:    dict[SubPoolType, SubPool]

    week_games:   dict[int, list[Game]]
    game_picks:   dict[Game, dict[Swami, Pick]]
    week_picks:   dict[int, dict[Swami, GamePick]]
    week_scores:  dict[int, dict[Swami, Scores]]
    swami_scores: dict[Swami, WeekScores]
    tot_scores:   dict[Swami, Scores]

    def __init__(self, name: str, season: int, **kwargs):
        """Note that the swamis for this pool are generally specified in the
        config file entry, but may be overridden in `kwargs`
        """
        pools = cfg.config('pools')
        if name not in pools:
            raise RuntimeError(f"Pool '{name}' is not known")
        pool_info = pools[name]
        # if `swamis` specified in `kwargs`, replaces config file list (no merging)
        swamis = kwargs.pop('swamis', None) or pool_info.get('swamis')

        self.name      = name
        self.season    = season
        self.swamis    = {}
        self.sub_pools = {}
        # idx is used below as a count of the inbound swamis
        for idx, swami in enumerate(swamis):
            if isinstance(swami, str):
                swami = Swami.get_by_name(swami)
            self.swamis[swami.name] = swami
        if len(self.swamis) < 1:
            raise RuntimeError("At least one swami must be specified")
        if len(self.swamis) < idx + 1:
            raise RuntimeError("Swami names must be unique")
        # populated by `run()`
        self.week_games   = {}
        self.game_picks   = {}
        self.week_picks   = {}
        # populated by `compute_results()`
        self.week_scores  = {}
        self.swami_scores = {}
        self.tot_scores   = {}

    def run(self, weeks: Iterable[int] = None) -> None:
        """Tabulate picks for the season from the competing swamis
        """
        query = Game.select().where(Game.season == self.season)
        if weeks:
            query = query.where(Game.week << list(weeks))
        query = query.order_by(Game.season, Game.week, Game.datetime)

        log.debug("Pool games SQL: " + query_to_string(query))
        games = query.execute()

        for week, wk_games in groupby(games, key=attrgetter('week')):
            if week not in self.week_games:
                self.week_games[week] = []
            for game in wk_games:
                self.week_games[week].append(game)
                self.game_picks[game] = {}
                if week not in self.week_picks:
                    self.week_picks[week] = {}
                for swami in self.swamis.values():
                    log.debug(f"Picks for week {week}, game {game.matchup}, swami {swami}")
                    pick = swami.get_pick(game.get_info())
                    if not pick:
                        continue
                    if swami not in self.week_picks[week]:
                        self.week_picks[week][swami] = {}
                    self.game_picks[game][swami] = pick
                    self.week_picks[week][swami][game] = pick

        if not self.game_picks:
            raise RuntimeError("No games selected")
        self.compute_results()

    def compute_results(self) -> None:
        """Use the data in `self.game_picks` and actual game results to populate
        the following variables:
          `self.week_scores`  - used to determine weekly winners
          `self.tot_scores`   - used to determine season winners
          `self.swami_scores` - used for `print_results()`

        Note that the results are not sorted within these fields; it is up to the
        caller to sort, see `get_winner()` for examples
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
                if not scores[1].is_empty():
                    self.swami_scores[swami][week][1] += scores[1]
                    self.week_scores[week][swami][1] += scores[1]
                    self.tot_scores[swami][1] += scores[1]

    def get_sub_pool(self, sp_type: SubPoolType) -> SubPool:
        """Initializes and returns the pool run instance; it is up to the caller
        to actually run it (for now!!!).
        """
        if sp_type not in self.sub_pools:
            self.sub_pools[sp_type] = SubPool(self, sp_type)
        return self.sub_pools[sp_type]

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

    pool = Pool(name, season)
    pool.run(weeks)
    #su = pool.get_sub_pool(SubPoolType.SU)
    #su.print_results_md()
    ats = pool.get_sub_pool(SubPoolType.ATS)
    ats.print_results_md()
    pool.print_swami_bios_md()

    return 0

if __name__ == '__main__':
    sys.exit(main())
