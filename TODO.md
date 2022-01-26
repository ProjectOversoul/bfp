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
