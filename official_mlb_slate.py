from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import requests

MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
ET = ZoneInfo("America/New_York")


def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def _time_et(game_date: str) -> str:
    if not game_date:
        return ""
    try:
        dt = datetime.fromisoformat(game_date.replace("Z", "+00:00")).astimezone(ET)
        return dt.strftime("%-I:%M %p ET")
    except Exception:
        return ""


def _window(game_date: str) -> str:
    if not game_date:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(game_date.replace("Z", "+00:00")).astimezone(ET)
        return "Early" if dt.hour < 16 else "Late"
    except Exception:
        return "Unknown"


def fetch_official_mlb_slate(date_str: str | None = None, timeout: int = 15):
    """Official MLB slate from MLB StatsAPI. Returns one row per hitting side."""
    date_str = date_str or today_et()
    params = {"sportId": 1, "date": date_str, "hydrate": "probablePitcher,team"}
    r = requests.get(MLB_SCHEDULE_URL, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    rows = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            teams = g.get("teams", {})
            away = teams.get("away", {})
            home = teams.get("home", {})
            away_team = (away.get("team") or {}).get("name", "")
            home_team = (home.get("team") or {}).get("name", "")
            away_pitcher = (away.get("probablePitcher") or {}).get("fullName", "")
            home_pitcher = (home.get("probablePitcher") or {}).get("fullName", "")
            game_date = g.get("gameDate", "")
            game_pk = g.get("gamePk", "")
            status = (g.get("status") or {}).get("detailedState", "")
            game_key = f"{away_team} vs {home_team}"
            base = {
                "official_source": "MLB StatsAPI",
                "official_date": date_str,
                "game_pk": str(game_pk),
                "game_key": game_key,
                "game": game_key,
                "away_team": away_team,
                "home_team": home_team,
                "game_time_utc": game_date,
                "game_time_et": _time_et(game_date),
                "slate_window": _window(game_date),
                "game_status": status,
                "away_probable_pitcher": away_pitcher,
                "home_probable_pitcher": home_pitcher,
            }
            rows.append({**base, "team": away_team, "opponent": home_team, "pitcher": home_pitcher, "team_side": "away"})
            rows.append({**base, "team": home_team, "opponent": away_team, "pitcher": away_pitcher, "team_side": "home"})
    df = pd.DataFrame(rows)
    meta = {
        "source": "MLB StatsAPI",
        "date": date_str,
        "games": int(df["game_pk"].nunique()) if not df.empty and "game_pk" in df else 0,
        "team_rows": int(len(df)),
        "pulled_at_et": datetime.now(ET).isoformat(timespec="seconds"),
    }
    return df, meta


def official_game_count(df: pd.DataFrame | None) -> int:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return 0
    if "game_pk" in df.columns:
        s = df["game_pk"].dropna().astype(str).str.strip()
        s = s[(s != "") & (s != "nan")]
        if len(s):
            return int(s.nunique())
    if "game_key" in df.columns:
        s = df["game_key"].dropna().astype(str).str.strip()
        s = s[(s != "") & (s != "nan")]
        return int(s.nunique())
    return 0


def _norm(x: object) -> str:
    return str(x or "").strip().lower().replace(".", "")


def attach_official_slate_to_feed(feed_df: pd.DataFrame, slate_df: pd.DataFrame | None) -> pd.DataFrame:
    """Attach official game id/time/window/pitcher by hitter team. Does not alter hitter metrics."""
    if feed_df is None or not isinstance(feed_df, pd.DataFrame):
        return pd.DataFrame()
    out = feed_df.copy()
    if slate_df is None or not isinstance(slate_df, pd.DataFrame) or slate_df.empty:
        out["official_slate_attached"] = False
        return out

    slate = slate_df.copy()
    slate["_team_norm"] = slate["team"].map(_norm) if "team" in slate.columns else ""
    team_map = {r["_team_norm"]: r for _, r in slate.iterrows() if r.get("_team_norm")}
    attach_cols = [
        "game_pk", "game_key", "game", "game_time_et", "game_time_utc", "slate_window", "game_status",
        "away_team", "home_team", "away_probable_pitcher", "home_probable_pitcher", "pitcher",
        "opponent", "official_source", "official_date"
    ]
    matched = []
    for i, r in out.iterrows():
        key = _norm(r.get("team", ""))
        m = team_map.get(key)
        if m is not None:
            for c in attach_cols:
                if c in m.index:
                    out.at[i, c] = m[c]
            matched.append(True)
        else:
            matched.append(False)
    out["official_slate_attached"] = matched
    return out
