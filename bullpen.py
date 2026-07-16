def build_bullpen_card(team_data: dict | None) -> dict:
    team_data = team_data or {}
    hr9 = team_data.get("hr9")
    fatigue = team_data.get("fatigue")
    return {
        "team": team_data.get("team"),
        "hr9": hr9, "era": team_data.get("era"),
        "fatigue": fatigue, "recent_usage": team_data.get("recent_usage"),
        "risk_score": round((hr9 or 0) * .6 + (fatigue or 0) * .4, 3),
    }
