
# MLB Blender v133 Repeat Cut + Refill Runtime

Fixes the problem where old names were still showing as OWNER.

Changes:
- Repeat names are no longer just score-downgraded.
- If no strict repeat exception passes, they become event_role = ROTATED.
- ROTATED players show in audit/Game Board only, not as owners.
- Core/ALT/Chaos refill from fresh eligible players.
- Primary / Adjacent / WHO remain mutually exclusive.
