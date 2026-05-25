
# official_mlb_slate.py
# Official MLB schedule pull using MLB StatsAPI.
# This is slate context only. It does not pick hitters.

from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import pandas as pd

MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"

def _et_date(date_str=None):
    if date_str:
        return str(date_str)
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

def _fmt_time_et(iso_time):
    if not iso_time:
        return ""
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York"))
        return dt.strftime("%-I:%M %p ET")
    except Exception:
        return ""

def _slate_window(iso_time):
    if not iso_time:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York"))
        return "Early" if dt.hour < 16 else "Late"
    except Exception:
        return "Unknown"

def fetch_official_mlb_slate(date_str=None, timeout=12):
    date_str = _et_date(date_str)
    params = {
        "sportId": 1,
        "date": date_str,
        "hydrate": "probablePitcher,team"
    }
    r = requests.get(MLB_SCHEDULE_URL, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    rows = []
    dates = data.get("dates", [])
    for day in dates:
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
            game_key = f"{away_team} vs {home_team}".strip()

            base = {
                "official_source": "MLB StatsAPI",
                "official_date": date_str,
                "game_pk": game_pk,
                "game_key": game_key,
                "game": game_key,
                "away_team": away_team,
                "home_team": home_team,
                "game_time_utc": game_date,
                "game_time_et": _fmt_time_et(game_date),
                "slate_window": _slate_window(game_date),
                "game_status": status,
                "away_probable_pitcher": away_pitcher,
                "home_probable_pitcher": home_pitcher,
            }

            # Row for away hitters vs home pitcher.
            rows.append({
                **base,
                "team": away_team,
                "opponent": home_team,
                "pitcher": home_pitcher,
                "opponent_pitcher": home_pitcher,
                "team_side": "away",
            })
            # Row for home hitters vs away pitcher.
            rows.append({
                **base,
                "team": home_team,
                "opponent": away_team,
                "pitcher": away_pitcher,
                "opponent_pitcher": away_pitcher,
                "team_side": "home",
            })

    df = pd.DataFrame(rows)
    meta = {
        "source": "MLB StatsAPI",
        "date": date_str,
        "games": int(df["game_pk"].nunique()) if not df.empty and "game_pk" in df.columns else 0,
        "team_rows": int(len(df)),
        "pulled_at_et": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds"),
    }
    return df, meta

def official_game_count(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return 0
    if "game_pk" in df.columns:
        s = df["game_pk"].dropna().astype(str)
        s = s[s != ""]
        if len(s):
            return int(s.nunique())
    if "game_key" in df.columns:
        s = df["game_key"].dropna().astype(str).str.strip()
        s = s[s != ""]
        return int(s.nunique())
    return 0

def attach_official_slate_to_feed(feed_df, slate_df):
    """Attach official MLB game_pk/time/window/pitchers to parsed PDF rows by team/opponent/game_key."""
    if not isinstance(feed_df, pd.DataFrame) or feed_df.empty:
        return pd.DataFrame()
    if not isinstance(slate_df, pd.DataFrame) or slate_df.empty:
        out = feed_df.copy()
        out["official_slate_attached"] = False
        return out

    out = feed_df.copy()
    slate = slate_df.copy()

    def norm(x):
        return str(x or "").strip().lower()

    # team-level join first
    slate_team = slate.drop_duplicates(["team"]).set_index(slate["team"].map(norm))
    attached_cols = ["game_pk","game_key","game_time_et","slate_window","game_status","away_team","home_team","away_probable_pitcher","home_probable_pitcher","pitcher","opponent","official_source","official_date"]
    for c in attached_cols:
        if c not in out.columns:
            out[c] = out.get(c, "")

    matched = []
    for idx, r in out.iterrows():
        key = norm(r.get("team", ""))
        if key in slate_team.index:
            s = slate_team.loc[key]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[0]
            for c in attached_cols:
                if c in s.index:
                    # Do not overwrite hitter/player, but do fix game/time/window/opponent/pitcher context.
                    out.at[idx, c] = s[c]
            matched.append(True)
        else:
            matched.append(False)
    out["official_slate_attached"] = matched
    return out
