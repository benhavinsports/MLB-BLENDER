# MLB Blender v76 Zero-Fail Stability

Fixes:
- Removes every remaining fragile regex dependency from game-key creation.
- Adds guaranteed imports to engine.py and feeder.py.
- Live slate loader cannot crash the app.
- PDF upload path cannot crash the app; it fails safely with message instead.
- Feeder game_key creation no longer depends on re.
- Keeps v72/v75 live slate + Gate 19 + canonical game engine.
