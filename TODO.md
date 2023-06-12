### TODO Items/Ideas ###

#### Basic Platform ####
- Complete regular season vs. playoff sub-pool formats
  - Fix documentation for `pool` module
- Show weekly winners in pool repoting
- Test data and test cases for:
  - Analysis framework and filters
  - Pool results aggregation
- Cleanup and unify console scripts for consistent operation of the platform
  - data_mgr tool (command for clean data update)
  - pool_mgr tool
  - swami_mgr tool
- Add game\_info/line\_info timestamps to game table (set to file download timestamp)
  - Move line information to separate table???
- Add data source for current points spreads and over/under (i.e. for upcoming games),
  needed when human swamis come online
- Automated loading of base data (from PFR, current line data source, and FTE)
- Simple GUI for running and reporting on pools/runs
- Documentation for extending base data and models
  - Games (more stats)
  - Teams (standings, stats, rosters, team matchups, etc.)
  - Players (stats, player matchups, plus-minus, injuries, etc.)
- Documentation for extending analysis class/framework

#### Future Enhancements ####

- Add nlfswamis-style pool rules
  - Weekly winners
  - Regular season winners
  - Playoff pool
  - Min/required game picks
  - Total point tie-breaker
- Let SwamiCyberBasic use separate analysis for SU and ATS
- Add confidence levels and betting to competitions
- Implement SwamiHuman, as part of a web-based pool management platform

#### Known Bugs ####
- In `__main__.py` for `swamis.load_data()` does not actually reload the data as it currently says. Current bandaid is just skipping the swamis that need to be reloaded.
  - ERROR CODE <span style="color:red;">#001</span>
  - Possible Fixes:
    - Change to upsert model for loading swami database?
    - Change from throwing skip warning to actually removing and replacing data?
- `pfr.py` what session.get returns is not a request but a response
  - error code <span style="color:red;">#002</span>
  - Possible Fixes: 
    - Change the nomenclature to be more accurate to the actual return type.
- When fetching line data using `pfr.load_line_data` there is no error trapping for dates prior to the teams establishment date.
  - error code <span style="color:red;">#003</span>
  - Possible Fixes:
    - Error trap based on team meta data for establishment date?
