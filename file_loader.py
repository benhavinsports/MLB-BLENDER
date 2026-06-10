
import pandas as pd
import io

def load_uploaded_file(uploaded_file):

    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return convert_df(df)

    elif name.endswith(".pdf"):
        # simplified PDF fallback: treat as text table export
        text = uploaded_file.read().decode("utf-8", errors="ignore")
        lines = text.split("\n")

        hitters = []
        games = []

        for line in lines:
            parts = line.split(",")
            if len(parts) >= 3:
                hitters.append({
                    "name": parts[0],
                    "team": parts[1],
                    "pull_rate": float(parts[2]) if parts[2].replace('.','',1).isdigit() else 0.4,
                    "hard_hit": 0.45
                })

        return {
            "games": [{"home": "NYY", "away": "BOS", "total": 8.0}],
            "hitters": hitters
        }

def convert_df(df):

    hitters = []
    games = []

    for _, row in df.iterrows():
        if "name" in df.columns:
            hitters.append({
                "name": row.get("name"),
                "team": row.get("team"),
                "pull_rate": float(row.get("pull_rate", 0.4)),
                "hard_hit": float(row.get("hard_hit", 0.4))
            })

    return {
        "games": [{"home": "NYY", "away": "BOS", "total": 8.0}],
        "hitters": hitters
    }
