### TODO Items/Ideas ###

#### Basic Platform ####
- Add ATS pools to `pool` module
- Implement SwamiLasVegas based on historical and current odds information
- Test data and test cases for:
  - Analysis framework and filters
  - Pool results aggregation
- Add game\_info/line\_info timestamps to game table (set to file download timestamp)
  - Move line information to separate table???
- Add data source for current points spreads and over/under (i.e. for upcoming games)
- Cleanup and unify console scripts for consistent operation of the platform
  - data_mgr tool (command for clean data update)
  - pool_mgr tool
  - swami_mgr tool
- Automated loading of base data (from PFR, current line data source, and FTE)
- Simple GUI for running and reporting on pools/runs
- Documentation for extending base data and models
  - Games (more stats)
  - Teams (standings, stats, rosters, team matchups, etc.)
  - Players (stats, player matchups, plus-minus, injuries, etc.)
- Documentation for extending analysis class/framework

#### Future Enhancements ####

- Add nlfswamis-style pool rules
- Add confidence levels and betting to competitions
- Implement SwamiHuman, as part of a web-based pool management platform
