# MLB Blender v80 Full Live Elimination Machine

Adds the remaining upgrade layer:
- Public live hitter metric ingestion from Baseball Savant when available.
- Public MLB roster hitter pool + MLB public slate/pitcher context.
- Uploaded feeds override/fill live public metrics.
- Live metrics fill pull%, sweet spot%, barrel%, hard-hit%, DMG proxy, HPI/HR proxy when available.
- Pitch edge is never faked; missing pitch-type context kills the pitch gate instead of creating fake owners.
- True elimination-first flow: score cannot create owners.
- Adaptive model weights recalibrate from recap outcome patterns only, never player-name recycling.
- RECALIBRATE MODEL WEIGHTS button added.
- Gate 19 remains final confirmation only.
