# VERSION HISTORY

v132: Clean unified engine runtime.
v133: Repeat cut/refill so stale repeat names stop owning.
v134: Upload/run parse experiment; not results-system focus.
v135: Import compatibility restore.
v136: Full app/ui import compatibility, including csv_bytes.
v137: Stable board gate trace + no-crash attempt.
v139: README/version history restoration only. No engine logic change.

v140: Board memory/results sync. Restores board-game style PASS/SOFT/CUT rendering without deleting README history.

v141: README preserved from uploaded master README; appended board-memory sync details only. No README stripping.

v142: Clean production strengthened. Consolidated runtime files instead of patch stacking; production package only.

v143: Board renderer and team count fix. Fixed literal board_lane_summary text and strengthened dashboard counts.

v144: Ticket timeframe + SGP environment finder. Filters tickets by early/late/full/custom window and only shows SGP when Blender flags the environment.

v145: Startup feeder fix. Restored feeder.read_feed so app.py starts.

v146: Startup + ticket import fix. Stable feeder.read_feed and engine.run_ticket_view exports.

v148: Correct clean runtime. Clean feeder.py + engine.py replacement.

v149: Restored Blender Experience. Board-game visual renderer and ticket display restored on top of v148 clean engine.
