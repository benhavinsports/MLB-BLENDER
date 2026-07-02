import requests

def get_probable_starter(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        pitchers = data.get("gameData", {}).get("probablePitchers", {})

        away = pitchers.get("away", {}).get("fullName", "unknown")
        home = pitchers.get("home", {}).get("fullName", "unknown")

        return {
            "away": away,
            "home": home
        }

    except:
        return {
            "away": "unknown",
            "home": "unknown"
        }
