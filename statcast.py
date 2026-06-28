
from pybaseball import statcast_batter

def get_batter_statcast(player_id):
    try:
        data = statcast_batter("20250101", "20251231", player_id)
        return {
            "barrel": data["launch_speed"].mean() if len(data)>0 else 0,
            "ev": data["launch_speed"].mean() if len(data)>0 else 0,
            "hh": (data["launch_speed"] > 95).mean() if len(data)>0 else 0
        }
    except:
        return {"barrel":0,"ev":0,"hh":0}
