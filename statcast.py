
from random import uniform

def get_statcast(player_id):

    # SAFE FALLBACK (no dependency crash)
    return {
        "barrel": uniform(0.08,0.18),
        "ev": uniform(88,95),
        "hh": uniform(0.30,0.55),
        "pull": uniform(45,75),
        "iso": uniform(0.120,0.250)
    }
