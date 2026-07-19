from __future__ import annotations

from functools import lru_cache

from services.http import get_json

TEAM_STATS_URL = "https://statsapi.mlb.com/api/v1/teams/{team_id}/stats"


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=128)
def _team_pitching(team_id: int, season: int) -> dict:
    """MLB team pitching fallback used when a true bullpen feed is unavailable."""
    data = get_json(
        TEAM_STATS_URL.format(team_id=team_id),
        params={"stats": "season", "group": "pitching", "season": season},
    )
    blocks = data.get("stats") or []
    splits = ((blocks[0] or {}).get("splits") or []) if blocks else []
    stat = (splits[0].get("stat") or {}) if splits else {}
    ip = _number(stat.get("inningsPitched"))
    hr = _number(stat.get("homeRuns"))
    return {
        "hr9": (hr * 9 / ip) if hr is not None and ip else None,
        "era": _number(stat.get("era")),
        "source": "TEAM_PITCHING_PROXY",
    }


def build_bullpen_card(
    team_data: dict | None,
    *,
    team_id: int | None = None,
    season: int | None = None,
    team_name: str | None = None,
) -> dict:
    team_data = dict(team_data or {})
    if team_id and season:
        for key, value in _team_pitching(int(team_id), int(season)).items():
            if team_data.get(key) is None and value is not None:
                team_data[key] = value

    hr9 = _number(team_data.get("hr9"))
    era = _number(team_data.get("era"))
    fatigue = _number(team_data.get("fatigue"))

    components = []
    if hr9 is not None:
        components.append(min(10.0, hr9 / 1.35 * 6.0))
    if era is not None:
        components.append(min(10.0, era / 4.50 * 4.0))
    if fatigue is not None:
        components.append(min(10.0, fatigue))

    risk_score = round(sum(components), 3) if components else None
    return {
        "team": team_data.get("team") or team_name,
        "team_id": team_id,
        "hr9": hr9,
        "era": era,
        "fatigue": fatigue,
        "recent_usage": team_data.get("recent_usage"),
        "risk_score": risk_score,
        "loaded": risk_score is not None,
        "source": team_data.get("source") or ("SUPPLIED" if team_data else "UNAVAILABLE"),
    }
