# MLB Blender v73 Live Public Bugfix

Fixes:
- LOAD LIVE PUBLIC SLATE crash from missing `re` import.
- Adds missing live loader imports: re, json, urllib.request.
- Makes team_abbr safer so public slate loading does not crash on weird team strings.
- Keeps v72 live public slate + Gate 19 true model upgrades.
