
# MLB Blender v132 Clean Unified Runtime

This build replaces the stacked patch engine with one clean runtime.

Single pipeline:
1. Read current uploaded feed only
2. Remove fake/synthetic rows
3. Normalize player/team/pitcher from PDF
4. Evaluate event role once: Primary / Adjacent / WHO / CUT
5. Apply score caps from weak gates
6. Rotate repeat names down instead of hard-blocking
7. Build Core 3 as Primary / Adjacent / WHO
8. Highlight strongest 2 inside Core 3
9. Build ALT 3 and Chaos 3 without duplicate players

No old proof patch files are required for runtime.
