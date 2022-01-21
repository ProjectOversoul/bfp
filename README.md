# BFP - Basic Football Platform #

## Overview ##

This project implements a framework upon which algorithms for predicting the results of
NFL football games can be developed, tabulated against actual game outcomes, and evaluated
against other algorithms.

The objective here is not to build the ultimate football stats/prediction platform, but
rather to outline a high-level design, which can then be extended and enhanced to include
additional algorithmic and human participation.  The foundation exists for being able to
run configurable, on-going competitive pools for both silicon- and carbon-based entities.

## Platform Objects ##

### Swami ###

A Swami is an entity that is able to predict the outcome of football games.  There are
four fundamental types of Swamis:

- `Cyber` - An algorithm coded and configured within the platform
- `External Data` - An external data source for current and/or historical picks
- `Interactive` - A human or an external algorithm interacting through a web app or API
- `Web3` - A crypto-based algorithm executed via dapps and smart contracts on the blockchain

Okay, just kidding on that last one--there are only three types of Swamis.

Each Swami is associated with an underlying subclass of the abstract `Swami` base class.
The only methods that need to be implemented by a subclass are:

| Method | Description |
| --- | --- |
| `__init__()` | to pre-process/validate configuration parameters, if needed |
| `get_pick(game_info)` | to get the Swami's pick for a specified game |

A "pick" consists of four components:

- Winner straight-up
- Winner against-the-spread
- Points margin
- Total points

The actual data structure returned by `get_pick()` looks like this:

```python
class Pick(NamedTuple):
    """Pick for an individual game, whether based on external data or computation
    from an internal algorithm
    """
    su_winner:  Team
    ats_winner: Team | None  # only if `pt_spread` is available
    pts_margin: int          # must be greater than 0
    total_pts:  int
```

It is up to individual pools to determine how the various elements of all of the game
picks are used to assess the standings and/or victors.  See "Running a Pool" below for
more detail on this.

#### Cyber Swamis ####

The initial set of Cyber Swamis on the platform are based on the `SwamiCyberBasic` class,
which works as follows:

1. Given a game to predict, the implementation specifies a set of past games to analyze,
   for both teams competing.  For instance, it may choose something like "last 5 games
   played against the opponent", "past two seasons against teams with winning records",
   "last home/away game played on a Thursday", etc.
2. Statistics are generated for the games being analyzed, one set for each team. Stats
   currently include: wins, losses, ties, points for/against, yards for/against, and
   turnovers for/against (as well as derivations thereof, such as percentages, averages,
   margins, etc.).
3. The statistics are then compared with each other, according to specified criteria, to
   determine the Swami's pick for the game.

The following configuration parameters are used to specify the number of games or seasons
to consider for analysis, as well as the selection criteria:

| Parameter | Description |
| --- | --- |
| `num_games` | Number of games to consider for analysis |
| `num_seasons` | Number of seasons to consider for analysis |
| `criteria` | List of stats to compare between teams in picking |

If both `num_games` and `num_seasons` are specified, `num_seasons` is used (and
`num_games` is ignored).  The stats available for `criteria` are as follows:

| Stat | Description |
| --- | --- |
| `games` | Number of games played in analysis set |
| `wins` | Number of wins |
| `win_pct` | Straight-up win percentage |
| `ats_wins` | Number of wins against the spread |
| `ats_win_pct` | Against-the-spread win percentage |
| `pts` | Average points margin |
| `yds` | Average yards margin |
| `tos` | Average turnover margin (take-aways) |

Note that "turnover margin" is computed such that a higher number continues to indicate
better team performance (that is, _not_ turnover give-aways), consistent with the other
`criteria` stats.

Cyber Swamis are defined in the `swamis.yml` configuration file.  The specification for a
swami might be done as such:

```yaml
---
default:
  swami_classes:
    SwamiVsTeam:
      swami_type:    cyber
      class_params:
        num_games:
        num_seasons:
        criteria:    [wins, pts, yds]
  swamis:
    Rudi 6:
      about_me:      "Pick based on last three matchups between teams"
      module_path:   pltform.swami
      swami_class:   SwamiVsTeam
      swami_params:
        num_games:   3
```

Note that Swamis (e.g. "Rudi 6, here) are defined on top of a `swami_class`, which is a
subclass of `SwamiCyberBasic`.  Any of the parameters specified under the named class in
`swami_classes` (`SwamiVsTeam`, in this case) are inherited, or may be overridden, by the
specific Swami entry.  In this example, the `criteria` configuration specifies that for
the two teams in a matchup, and the set of games under analysis on each side, the stats
compared will be: (1) aggregated wins; (2) points margin; and then (3) yards margin--in
that order.  The first comparison that favors one team or the other will determine the
selected pick for the algorithm.

The code in the Swami implementation class (e.g. `SwamiVsTeam`) determines the details of
which games are considered by instantiating an `Analysis` object and adding "filters" that
will be applied to the database of past games (these will be discussed in the "Analysis"
section).  The implementation class also determines how the against-the-spread pick and
values for points margin and total points are computed.

The initial set of `SwamiCyberBasic` implementations are as follows:

| Subclass | Description |
| --- | --- |
| `SwamiVsAll` | Analyze all games (against any opponent) |
| `SwamiVsTeam` | Analyze games against opposing team (i.e. head-to-head) |
| `SwamiVsDiv` | Analyze games against opposing team's division |
| `SwamiVsConf` | Analyze games against opposing team's conference |

Additional implementation classes may be added for any number and/or combination of the
analysis filters described below.

#### External Data Swamis ####

There are currently two External Data Swamis planned (though not yet implemented):

- `SwamiLasVegas` - Used to source current and historical odds data (spreads and
  over-unders), as well as serve as a baseline competitor in straight-up and points-margin
  pool competitions.
- `SwamiFiveThirtyEight` - The gold-standard for data-driven predictions.  One of the
  inspirations for this overall project is TK's bold pronouncement that his algorithms can
  beat FiveThirtyEight.  We'll see.

#### Interactive Swamis ####

There are no specific designs for Interactive Swamis yet, but two possible implementations
for participation in live pools can be envisioned:

- `SwamiHuman` - Integration with an internal web-app (yet to be developed) for human
  participation in an ongoing pool.
- `SwamiAPI` - Integration with an API server for enabling external entities (whether
  organics or machines) to participate in an ongoing pool.

### Analysis ###

An `Analysis` object may be instantiated to generate the two sets of stats (one for each
team) needed for predicting the outcome of a game.

Note that the current design and implementation of the `Analysis` class is just one way of
approaching game predictions, and is tightly coupled with the `SwamiCyberBasic` class (and
as such, should/will be renamed to `AnlyBasic`, or something like that).  The intent is to
demonstrate an abstract pattern for Analysis classes in general, which can then be used by
other families of Cyber Swami implementations.  Future Analysis classes may or may not
have similar filter mechanisms and/or computed stats on which to base picks.  Additional
sources/types of data (e.g. venue/weather data, team/roster data, player/injury data,
etc.) may be available for next-generation analysis classes.

#### Filters ####

As mentioned above, for the initial `Analysis` class, filters are chosen to narrow the
scope of past games from which to aggregate the stats.  The current list of filters is as
follows (all subclassed from `AnlyFilter`):

| Filter | General Description |
| --- | --- |
| `AnlyFilterVenue`* | Home or away games |
| `AnlyFilterTeam` | Head-to-head matchups against specified team |
| `AnlyFilterDiv` | Games against specified division |
| `AnlyFilterConf` | Games against specified conference |
| `AnlyFilterWeeks` | Week(s) within the season (e.g. early/mid/late season, playoff round, etc.) |
| `AnlyFilterDayOfWeek`* | Day of the week (e.g. Thursday, Sunday, Monday) |
| `AnlyFilterRecord`* | Games against teams with specified season record (range) |
| `AnlyFilterRanking`* | Games against teams with specified team ranking (e.g. top 5 total offense) |
| `AnlyFilterSpreaad`* | Games with specified points spread (e.g. favored by more than 10) |
| `AnlyFilterOutcome`* | Games with specified outcome (e.g. only wins, losses, or ties) |
| `AnlyFilterStatMargin`* | Games with specified stats margin (e.g. won by less than 7) |

\* indicates filters not yet implemented

Note that filters are written in "general" terms, so that the manner in which they are
applied can be arbitrary (i.e. not directly correlated with the game at hand).  However,
the intended use cases are related to the context of the game under analysis.  Thus, the
following table describes the intended use cases, which must be implemented within the
`Swami` subclasses utilizing the `Analysis` framework:

| Filter | Intended Use Case |
| --- | --- |
| `AnlyFilterVenue` | Home or away game, consistent with current matchup |
| `AnlyFilterTeam` | Head-to-head matchups against current opponent |
| `AnlyFilterDiv` | Games against current opponent's division |
| `AnlyFilterConf` | Games against current opponent's conference |
| `AnlyFilterWeeks` | Week within the season, similar to current matchup (e.g. early/late season, playoff round, etc.) |
| `AnlyFilterDayOfWeek` | Day of the week, similar to current matchup (e.g. Monday Night game) |
| `AnlyFilterRecord` | Games against teams with record similar to current opponent (specify similarity range) |
| `AnlyFilterRanking` | Games against teams with team rankings similar to current opponent (specify similarity range) |
| `AnlyFilterSpreaad` | Games with points spread similar to current odds (specify similarity range)

#### Statistics ####

The following is the stats structure generated for each team in the analysis:

```python
class AnlyStats(NamedTuple):
    """Note that we record `games`, `wins`, `losses`, etc. as lists of games
    (rather than just the count), so the underlying detail-level information
    is readily available to the analysis class.  The count for each type of
    result is available as a derived property
    """
    games:       list[Game]
    wins:        list[Game]
    losses:      list[Game]
    ties:        list[Game]
    ats_wins:    list[Game]  # wins against the spread (beat or cover)
    pts_for:     int
    pts_against: int
    yds_for:     int
    yds_against: int
    tos_for:     int  # committed by current team
    tos_against: int  # committed by opponent
```

In addition to the stats fields listed above, the following are provided as additional
computed fields (implemented as "properties"):

- `num_games`
- `num_wins`
- `num_losses`
- `num_ties`
- `num_ats_wins`
- `win_pct`
- `loss_pct`
- `ats_win_pct`
- `pts_margin`
- `total_pts`
- `yds_margin`
- `total_yds`
- `tos_margin`
- `total_tos`

### Game ###

Currently, all of the data available within the platform for analysis, picks, and running
pools comes from game-level data.

#### Game Info ####

The following is the `GameInfo` structure that is passed to the `Swami` implementations
when getting their picks:

```python
class GameInfo(NamedTuple):
    id:           int
    season:       int    # year of season start
    week:         Week   # ordinal within season, or special `PlayoffWeek` value
    day:          WeekDay
    datetime:     datetime
    home_team:    Team
    away_team:    Team
    neutral_site: bool
    pt_spread:    float | None  # "pick" is represented by 0.0
    over_under:   float | None
```

Typically, this structure is passed through to the `Analysis` class, from which the stats
may be computed, as described above.

#### Game Results ####

The following is the `GameResult` structured that is then used by the pool implementation
to determine the standings/outcome of a pool "run" (e.g. a partial or full season):

```python
class GameResults(NamedTuple):
    winner:         Team
    loser:          Team
    is_tie:         bool
    winner_pts:     int
    loser_pts:      int
    pts_margin:     int
    total_pts:      int
    home_vs_spread: float | None
    away_vs_spread: float | None
    vs_over_under:  float | None
```

## Running a Pool ##

_Coming soon..._

## Technical Information ##

Requires Python 3.10 or higher.

Utilizes the following underlying technologies/libraries:

- [SQLite](https://www.sqlite.org/index.html) - as the RDBMS (Python Standard Library
  interface)
- [Peewee](https://pypi.org/project/peewee/) - as the ORM (nice library!)
- [Requests](https://pypi.org/project/requests/) - for HTTP requests
- [Beautiful Soup](https://pypi.org/project/beautifulsoup4/) - for HTML processing

## Enhancement Ideas ##

- Implement additional Analysis filters and Cyber Swamis (both algorithms and
  configurations) on the current `Analysis` class model
- Implement new Analysis paradigms, incorporating additional sources/types of data,
  including:
  - Games (more stats)
  - Teams (standings, stats, rosters, team matchups, etc.)
  - Players (stats, player matchups, plus-minus, injuries, etc.)
- Pool Manager tool for organizing, configuring, operating, and reporting on on-going
  pools
- Web-based frontend to allow humans to participate in on-going pools

## License ##

This project is licensed under the terms of the MIT License.

## Credits ##

All of the NFL game data (including historical Vegas lines) used by this application comes
from [Pro Football Reference](https://www.pro-football-reference.com/).

The author would like to acknowledge Mike Grau, who ran a great football pool for many
years.  The Pool component of this project draws inspiration from the format established
by his (now defunct) nflswamis.com site.  I don't know if Mike would approve of humans
delegating their picks to computational algorithms.
