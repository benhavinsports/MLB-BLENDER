from __future__ import annotations

from functools import lru_cache
from services.http import get_json

PEOPLE_URL = "https://statsapi.mlb.com/api/v1/people/{player_id}/stats"


def _f(value):
    try: return float(value)
    except (TypeError, ValueError): return None


@lru_cache(maxsize=256)
def _season_pitching(player_id: int, season: int) -> dict:
    data = get_json(PEOPLE_URL.format(player_id=player_id), params={"stats":"season", "group":"pitching", "season":season})
    blocks = data.get("stats") or []
    splits = (blocks[0].get("splits") or []) if blocks else []
    stat = (splits[0].get("stat") or {}) if splits else {}
    ip = _f(stat.get("inningsPitched"))
    hr = _f(stat.get("homeRuns"))
    so = _f(stat.get("strikeOuts"))
    bf = _f(stat.get("battersFaced"))
    return {
        "hr9": (hr * 9 / ip) if hr is not None and ip else None,
        "k_rate": (so / bf * 100) if so is not None and bf else None,
        "era": _f(stat.get("era")),
    }


def build_pitcher_card(pitcher, season: int) -> dict:
    if isinstance(pitcher, str):
        pitcher = {"name": pitcher}
    pitcher = pitcher or {}
    card = {
        "id": pitcher.get("id"), "name": pitcher.get("name") or "UNKNOWN",
        "side": pitcher.get("side"), "team": pitcher.get("team"),
        "hr9": None, "barrel_allowed": None, "xwoba_allowed": None,
        "hard_hit_allowed": None, "k_rate": None,
        "pitch_predictability": None, "platoon_weakness": "NEUTRAL",
    }
    if card["id"]:
        card.update({k:v for k,v in _season_pitching(int(card["id"]), season).items() if v is not None})
    card["leak_score"] = calculate_leak_score(card)
    return card


def calculate_leak_score(p: dict) -> float:
    # Normalize percentage inputs to comparable 0-10 contributions.
    hr9 = p.get("hr9") or 0
    barrel = (p.get("barrel_allowed") or 0) / 10
    xwoba = (p.get("xwoba_allowed") or 0) * 10
    hard = (p.get("hard_hit_allowed") or 0) / 10
    k = (p.get("k_rate") or 0) / 10
    predict = p.get("pitch_predictability") or 0
    return round(hr9 * 2 + barrel * 1.5 + xwoba * 1.2 + hard - k * .8 + predict, 3)
