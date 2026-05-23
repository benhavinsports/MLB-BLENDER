# BLENDER 1-5 EFFECTIVE ENGINE BUILD

This implements the full requested 1-5:

1. Smart parser first
   - stronger PDF/CSV/XLSX/TXT parser
   - normalizes Pull, HH, Barrel, DMG/ULT/ADJ, HPI, HR lane, pitch edge, lineup slot

2. Validator before Blender
   - feed validation stored in meta
   - rows with weak/name-only data become audit-only

3. True Blender engine
   - gate-strength Blender score
   - no alphabetical/random picks
   - no fake recovery tickets

4. AI Oil
   - parser/validator/audit support only
   - does not pick players by itself

5. UI stability
   - duplicate download keys fixed
   - live pull and spinner preserved
