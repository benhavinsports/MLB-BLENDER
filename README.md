# THE BLENDER v45 Clean Rebuild

This is a reset build.

Architecture:
1. feeder.py      — reads PDF/CSV/XLSX into raw rows
2. schema.py      — normalizes names, teams, metrics, constants
3. audit.py       — blocks bad feeds before picks
4. engine.py      — runs official Blender gates and one-owner-per-game logic
5. ui.py          — cinematic shell only, no logic
6. app.py         — app controller
7. sample_template.csv

Rules:
- No team abbreviation can become a player.
- No team name can become a player.
- No blank metric row can become a card.
- No full-slate run if games/teams/pitchers do not separate.
- Same-game core conflicts are blocked.
- UI never invents data.
- PDF is fallback; structured feed is preferred.
