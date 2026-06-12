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


def _participants(row: pd.Series) -> set[str]:
    vals = []
    for c in ["away_team", "home_team"]:
        if c in row.index and str(row.get(c, "")).strip():
            vals.append(_norm(row.get(c, "")))
    if not vals:
        g = str(row.get("game_key", row.get("game", "")) or "")
        if " vs " in g:
            vals.extend([_norm(x) for x in g.split(" vs ")[:2]])
    return set(vals)


def _same_game_key(a: object, b: object) -> bool:
    aa, bb = _norm(a), _norm(b)
    return bool(aa and bb and aa == bb)


def attach_official_slate_to_feed(feed_df: pd.DataFrame, slate_df: pd.DataFrame | None) -> pd.DataFrame:
    """Attach official slate data without ever cross-wiring a hitter to another game.

    V0215 binding rule:
    - preserve the PDF/feed game/team/pitcher in original_* columns
    - prefer exact PDF game_key match, then verify team is in that game
    - only fall back to team-only match when the feed row has no game_key
    - never overwrite a non-empty PDF game_key with a different official game
    """
    if feed_df is None or not isinstance(feed_df, pd.DataFrame):
        return pd.DataFrame()
    out = feed_df.copy()
    for c in ["game_key", "game", "team", "opponent", "pitcher"]:
        if c not in out.columns:
            out[c] = ""
    out["original_game_key"] = out["game_key"].astype(str)
    out["original_game"] = out["game"].astype(str)
    out["original_team"] = out["team"].astype(str)
    out["original_pitcher"] = out["pitcher"].astype(str)

    if slate_df is None or not isinstance(slate_df, pd.DataFrame) or slate_df.empty:
        out["official_slate_attached"] = False
        out["binding_status"] = "PDF_ONLY_NO_OFFICIAL_SLATE"
        return out

    slate = slate_df.copy()
    slate["_team_norm"] = slate["team"].map(_norm) if "team" in slate.columns else ""
    slate["_game_norm"] = slate["game_key"].map(_norm) if "game_key" in slate.columns else ""
    team_map = {r["_team_norm"]: r for _, r in slate.iterrows() if r.get("_team_norm")}
    game_rows = {}
    for _, r in slate.iterrows():
        g = r.get("_game_norm", "")
        if g:
            game_rows.setdefault(g, []).append(r)

    safe_attach_cols = [
        "game_pk", "game_time_et", "game_time_utc", "slate_window", "game_status",
        "away_team", "home_team", "away_probable_pitcher", "home_probable_pitcher",
        "official_source", "official_date"
    ]
    # These columns can be overwritten only after the binding is proven safe.
    identity_cols = ["game_key", "game", "pitcher", "opponent"]

    matched, statuses = [], []
    for i, r in out.iterrows():
        pdf_game = str(r.get("game_key", "") or r.get("game", "")).strip()
        team_norm = _norm(r.get("team", ""))
        chosen = None
        status = "NO_MATCH"

        # 1) Exact game first, because a team-only join is what created wrong cards.
        if pdf_game:
            candidates = game_rows.get(_norm(pdf_game), [])
            if candidates:
                if team_norm:
                    for m in candidates:
                        if team_norm in _participants(m):
                            chosen = m
                            status = "OFFICIAL_GAME_AND_TEAM_MATCH"
                            break
                    if chosen is None:
                        # Keep PDF binding and mark mismatch; do NOT team-map this row elsewhere.
                        status = "PDF_GAME_TEAM_MISMATCH_LOCKED_TO_PDF"
                else:
                    chosen = candidates[0]
                    status = "OFFICIAL_GAME_MATCH_TEAM_BLANK"

        # 2) Fall back to team-only only when PDF had no game to protect.
        if chosen is None and not pdf_game and team_norm:
            m = team_map.get(team_norm)
            if m is not None:
                chosen = m
                status = "OFFICIAL_TEAM_ONLY_MATCH_NO_PDF_GAME"

        if chosen is not None:
            for c in safe_attach_cols:
                if c in chosen.index:
                    out.at[i, c] = chosen[c]
            # Safe identity overwrite rules.
            for c in identity_cols:
                if c in chosen.index:
                    if c in ["game_key", "game"]:
                        if not pdf_game or status.startswith("OFFICIAL_GAME") or status.startswith("OFFICIAL_TEAM_ONLY"):
                            out.at[i, c] = chosen[c]
                    else:
                        # pitcher/opponent are side-specific; safe once chosen row is verified.
                        out.at[i, c] = chosen[c]
            matched.append(True)
        else:
            matched.append(False)
        statuses.append(status)

    out["official_slate_attached"] = matched
    out["binding_status"] = statuses
    return out
