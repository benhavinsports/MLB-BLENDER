import requests


def get_pitcher_profile(name):

    """
    REAL MLB SIGNAL MODEL (SAFE VERSION)

    Uses MLB StatsAPI + heuristic enrichment
    NO external paid dependencies
    """

    if not name or name == "unknown":
        return {
            "weak_vs_right": 0.50,
            "weak_vs_left": 0.50,
            "park_factor": 1.00,
            "k_rate": 0.20,
            "bb_rate": 0.08,
            "hr_rate": 0.15,
            "type": "unknown"
        }

    try:
        # -------------------------
        # MLB PLAYER SEARCH
        # -------------------------
        search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={name}"
        search_data = requests.get(search_url, timeout=10).json()

        people = search_data.get("people", [])
        player_id = people[0]["id"] if people else None

        if not player_id:
            raise Exception("No player ID found")

        # -------------------------
        # PLAYER STATS
        # -------------------------
        stats_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}?hydrate=stats(group=[pitching],type=[season])"
        stats_data = requests.get(stats_url, timeout=10).json()

        stats = stats_data.get("people", [{}])[0].get("stats", [])

        pitching = {}
        if stats:
            splits = stats[0].get("splits", [])
            if splits:
                pitching = splits[0].get("stat", {})

        # -------------------------
        # EXTRACT REAL SIGNALS
        # -------------------------
        k_rate = float(pitching.get("strikeOuts", 0)) / max(float(pitching.get("battersFaced", 1)), 1)
        bb_rate = float(pitching.get("baseOnBalls", 0)) / max(float(pitching.get("battersFaced", 1)), 1)
        hr_rate = float(pitching.get("homeRuns", 0)) / max(float(pitching.get("battersFaced", 1)), 1)

        era = float(pitching.get("era", 4.00))

        # -------------------------
        # WEAKNESS MODELING (REALISTIC SIGNAL MAP)
        # -------------------------
        weak_vs_right = 0.5
        weak_vs_left = 0.5

        if era > 4.50:
            weak_vs_right += 0.10
            weak_vs_left += 0.10

        if hr_rate > 0.03:
            weak_vs_right += 0.10

        if k_rate < 0.18:
            weak_vs_left += 0.10

        # -------------------------
        # PITCH TYPE CLASSIFICATION (ENHANCED)
        # -------------------------
        if k_rate > 0.25:
            pitcher_type = "strikeout_power"
        elif bb_rate > 0.10:
            pitcher_type = "wild_control"
        elif hr_rate > 0.03:
            pitcher_type = "flyball_risk"
        else:
            pitcher_type = "balanced"

        # -------------------------
        # PARK FACTOR (SAFE DEFAULT)
        # -------------------------
        park_factor = 1.05 if hr_rate > 0.03 else 1.00

        return {
            "weak_vs_right": min(weak_vs_right, 0.90),
            "weak_vs_left": min(weak_vs_left, 0.90),
            "park_factor": park_factor,
            "k_rate": round(k_rate, 3),
            "bb_rate": round(bb_rate, 3),
            "hr_rate": round(hr_rate, 3),
            "type": pitcher_type
        }

    except:

        # SAFE FALLBACK (NEVER FLAT, STILL DIFFERENTIABLE)
        return {
            "weak_vs_right": 0.55,
            "weak_vs_left": 0.55,
            "park_factor": 1.00,
            "k_rate": 0.20,
            "bb_rate": 0.08,
            "hr_rate": 0.15,
            "type": "fallback"
        }
