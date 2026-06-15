
import math
import requests

BASE = "https://statsapi.mlb.com/api/v1"
_schedule_cache = {}
_boxscore_cache = {}

def get_schedule(game_date):
    if game_date in _schedule_cache:
        return _schedule_cache[game_date]
    url = f"{BASE}/schedule?sportId=1&date={game_date}"
    data = requests.get(url, timeout=20).json()
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            games.append({
                "gamePk": g["gamePk"],
                "home": g["teams"]["home"]["team"],
                "away": g["teams"]["away"]["team"]
            })
    _schedule_cache[game_date] = games
    return games

def get_boxscore(game_pk):
    if game_pk in _boxscore_cache:
        return _boxscore_cache[game_pk]
    url = f"{BASE}/game/{game_pk}/boxscore"
    data = requests.get(url, timeout=20).json()
    _boxscore_cache[game_pk] = data
    return data

def _safe(v):
    return 0 if v in (None, "") else v

def _gate(value):
    return "PASS" if value else "FAIL"

def _evaluate_player(player_name, stat):
    ab = _safe(stat.get("atBats", 0))
    h = _safe(stat.get("hits", 0))
    d2 = _safe(stat.get("doubles", 0))
    d3 = _safe(stat.get("triples", 0))
    hr = _safe(stat.get("homeRuns", 0))
    bb = _safe(stat.get("baseOnBalls", 0))
    k = _safe(stat.get("strikeOuts", 0))

    audit = {"player_name": player_name}
    gates = {}

    def fail(g):
        gates[g] = "FAIL"
        audit["gates"] = gates
        return None, audit

    gates["G0"] = _gate(player_name is not None)
    if player_name is None:
        return fail("G0")

    gates["G1"] = _gate(ab > 0)
    if not ab > 0:
        return None, {"player_name": player_name, "gates": gates}

    gates["G2"] = _gate(h <= ab)
    if not (h <= ab):
        return fail("G2")

    contact = h / max(ab, 1)
    power = (d2 + d3 + hr) / max(ab, 1)
    iso = (d2 + (2 * d3) + (3 * hr)) / max(ab, 1)
    singles = h - d2 - d3 - hr
    total_bases = singles + (2 * d2) + (3 * d3) + (4 * hr)
    production = total_bases / max(ab, 1)
    strike = k / max(ab, 1)
    discipline = bb / max(ab, 1)
    expected = (
        0.25 * contact +
        0.25 * production +
        0.20 * power +
        0.10 * discipline -
        0.20 * strike
    )
    matchup = 0.5 - strike + (power * 0.1)
    event = (
        0.28 * production +
        0.16 * contact +
        0.18 * iso +
        0.12 * discipline +
        0.20 * matchup -
        0.06 * strike
    )

    checks = [
        ("G3", contact > 0.05),
        ("G4", power >= 0),
        ("G5", iso >= 0),
        ("G6", strike < 0.7),
        ("G7", discipline >= 0),
        ("G8", production > 0),
        ("G9", total_bases >= 0),
        ("G10", contact <= 1),
        ("G11", power <= 1),
        ("G12", iso <= 10),
        ("G13", strike >= 0),
        ("G14", discipline <= 1),
        ("G15", math.isfinite(event)),
        ("G16", math.isfinite(expected)),
        ("G17", math.isfinite(matchup)),
    ]

    for g, ok in checks:
        gates[g] = _gate(ok)
        if not ok:
            return None, {"player_name": player_name, "gates": gates}

    integrity = all(v is not None for v in [ab, h, d2, d3, hr, bb, k])
    gates["G18"] = _gate(integrity)
    if not integrity:
        return None, {"player_name": player_name, "gates": gates}

    row = {
        "player_name": player_name,
        "AB": ab,
        "H": h,
        "2B": d2,
        "3B": d3,
        "HR": hr,
        "BB": bb,
        "K": k,
        "CONTACT_RATE": contact,
        "POWER_RATE": power,
        "ISO_POWER": iso,
        "TOTAL_BASES": total_bases,
        "PRODUCTION_RATE": production,
        "STRIKEOUT_RISK": strike,
        "DISCIPLINE_INDEX": discipline,
        "EXPECTED_SCORE": expected,
        "MATCHUP_PROXY": matchup,
        "EVENT_SCORE": event,
    }
    audit.update(row)
    audit["gates"] = gates
    return row, audit

def evaluate_game(game_pk):
    data = get_boxscore(game_pk)
    players = []
    audit = []

    for side in ("home", "away"):
        team = data.get("teams", {}).get(side, {})
        for pdata in team.get("players", {}).values():
            person = pdata.get("person", {})
            stats = pdata.get("stats", {}).get("batting", {})
            row, a = _evaluate_player(person.get("fullName"), stats)
            audit.append(a)
            if row:
                players.append(row)

    players.sort(key=lambda x: x["EVENT_SCORE"], reverse=True)
    winner = players[0] if players else None
    return {"players": players, "winner": winner, "audit": audit}
