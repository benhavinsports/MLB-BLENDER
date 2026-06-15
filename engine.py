
import requests
from datetime import datetime

ESPN = "https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb"

def safe(x):
    return 0 if x is None else x

# ---------------------------
# DATA LAYER
# ---------------------------

def get_scoreboard(date=None):
    url = f"{ESPN}/scoreboard"
    if date:
        url += f"?dates={date}"
    return requests.get(url).json()

def extract_games(data):
    return data.get("events", [])

# ---------------------------
# G1: STARTER + MATCHUP ENGINE
# ---------------------------

def extract_pitchers(event):
    comps = event.get("competitions", [{}])[0]
    competitors = comps.get("competitors", [])

    pitchers = []
    for c in competitors:
        team = c.get("team", {}).get("name")
        prob = c.get("probables", [])
        pitchers.append({
            "team": team,
            "name": prob[0] if prob else "UNKNOWN"
        })
    return pitchers

def pitcher_archetype(name):
    # deterministic proxy (no external ML)
    if name == "UNKNOWN":
        return "BALANCED"
    if "R" in name:
        return "POWER_STRIKER"
    return "BALANCED"

def hitter_archetype(h):
    hr = safe(h.get("hr"))
    avg = safe(h.get("avg"))
    if hr > 25:
        return "POWER"
    if avg > 0.280:
        return "CONTACT"
    return "BALANCED"

def matchup_multiplier(p, h):
    if p == "POWER_STRIKER" and h == "POWER":
        return 0.85
    if p == "BALANCED" and h == "POWER":
        return 1.1
    return 1.0

# ---------------------------
# METRICS (G2-G19 CORE)
# ---------------------------

def compute(h):
    ab = safe(h.get("ab"))
    hits = safe(h.get("h"))
    d2 = safe(h.get("2b"))
    d3 = safe(h.get("3b"))
    hr = safe(h.get("hr"))
    bb = safe(h.get("bb"))
    k = safe(h.get("k"))

    singles = hits - d2 - d3 - hr
    tb = singles + 2*d2 + 3*d3 + 4*hr

    contact = hits / max(ab,1)
    power = (d2 + d3 + hr) / max(ab,1)
    iso = (d2 + 2*d3 + 3*hr) / max(ab,1)
    prod = tb / max(ab,1)
    risk = k / max(ab,1)
    disc = bb / max(ab,1)

    expected = (0.25*contact + 0.25*prod + 0.2*power + 0.1*disc - 0.2*risk)

    event = (0.3*prod + 0.2*iso + 0.2*contact + 0.1*disc - 0.1*risk)

    return expected, event

# ---------------------------
# ENGINE
# ---------------------------

def run(date=None, hitters=None):
    data = get_scoreboard(date)
    games = extract_games(data)

    results = []

    for g in games:
        pitchers = extract_pitchers(g)

        p_name = pitchers[0]["name"] if pitchers else "UNKNOWN"
        p_type = pitcher_archetype(p_name)

        # MOCK hitters if none provided (ESPN integration hook)
        if not hitters:
            hitters = [
                {"name":"Player A","ab":100,"h":30,"2b":8,"3b":1,"hr":5,"bb":10,"k":20},
                {"name":"Player B","ab":120,"h":40,"2b":10,"3b":2,"hr":12,"bb":15,"k":25},
            ]

        for h in hitters:
            h_type = hitter_archetype(h)
            m = matchup_multiplier(p_type, h_type)

            expected, event = compute(h)

            results.append({
                "player": h["name"],
                "game": g.get("name"),
                "score": event * m
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)
