
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Blender 16-Gate Visual Engine", layout="wide")

st.title("🧱 BLENDER 16-GATE VISUAL ENGINE")

st.caption("Strict sequential elimination system — no role assignment until Gate 16")

uploaded = st.file_uploader("Upload CSV (or use sample)", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
else:
    df = pd.DataFrame([
        {"name":"Player A","ISO":0.210,"SLG":0.480,"wOBA":0.360,"EV":91,"Barrel":15,"HH":47,"Pull":42,"FB":35},
        {"name":"Player B","ISO":0.160,"SLG":0.410,"wOBA":0.330,"EV":88,"Barrel":10,"HH":42,"Pull":38,"FB":28},
        {"name":"Player C","ISO":0.240,"SLG":0.520,"wOBA":0.390,"EV":93,"Barrel":21,"HH":52,"Pull":46,"FB":41},
    ])

st.subheader("Input Pool")
st.dataframe(df, use_container_width=True)

# -----------------------------
# 16-GATE ENGINE (VISUAL)
# -----------------------------

def run_gates(row):
    gates = []

    # G9–12 BATTER POWER CORE
    iso_ok = row["ISO"] >= 0.18
    slg_ok = row["SLG"] >= 0.40
    ev_ok = row["EV"] >= 89
    barrel_ok = row["Barrel"] >= 12

    power_fail = sum([not iso_ok, not slg_ok, not ev_ok, not barrel_ok])

    gates.append(("Gate 9 ISO", iso_ok))
    gates.append(("Gate 10 SLG", slg_ok))
    gates.append(("Gate 11 EV", ev_ok))
    gates.append(("Gate 12 Barrel", barrel_ok))

    # G13–14 SWING PROFILE
    pull_ok = row["Pull"] >= 40
    fb_ok = row["FB"] >= 30

    gates.append(("Gate 13 Pull%", pull_ok))
    gates.append(("Gate 14 FB%", fb_ok))

    # ELIMINATION LOGIC
    if power_fail >= 2:
        return "❌ ELIMINATED", gates

    if iso_ok and barrel_ok and ev_ok and row["HH"] >= 50:
        return "🟢 ELITE FINISHER", gates

    if pull_ok and fb_ok and power_fail == 0:
        return "🟡 STANDARD FINISHER", gates

    return "🟠 CHAOS SURVIVOR (WHO)", gates


results = []

for _, row in df.iterrows():
    status, gates = run_gates(row)

    results.append({
        "Player": row["name"],
        "Status": status,
        "Gate Breakdown": " | ".join([f"{g[0]}:{'PASS' if g[1] else 'FAIL'}" for g in gates])
    })

out = pd.DataFrame(results)

st.subheader("🧠 FINAL GATE 16 OUTPUT")
st.dataframe(out, use_container_width=True)

# -----------------------------
# VISUAL FILTER BOARD
# -----------------------------

st.subheader("📊 Live Status Board")

for r in results:
    st.write(f"**{r['Player']}** → {r['Status']}")
