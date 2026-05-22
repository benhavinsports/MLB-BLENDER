import streamlit as st
import pandas as pd
from engine import csv_bytes, run_recap_check


def inject_css():
    st.markdown('''
<style>
.stApp{background:#050806;color:#f4fff1}.block-container{max-width:980px;padding-top:1rem}
.header{border:1px solid rgba(160,255,90,.25);border-radius:22px;padding:16px;background:#071008;margin-bottom:12px}
.title{font-size:clamp(34px,7vw,64px);font-weight:1000;color:#caff5a;line-height:.95;text-align:center}
.sub{text-align:center;color:#87ff99;font-weight:900;letter-spacing:.18em}.machine{border:1px solid rgba(160,255,90,.22);border-radius:20px;padding:14px;background:#020302;margin:12px 0}.jar{height:180px;border:2px solid rgba(160,255,90,.45);border-radius:22px 22px 55px 55px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:center;background:radial-gradient(circle,rgba(202,255,90,.13),#071008)}
.chip{border:1px solid rgba(202,255,90,.35);border-radius:999px;padding:6px 10px;background:#111;color:#eaffbd;font-weight:800}.state{text-align:center;margin-top:8px;color:#caff5a;font-weight:900}.card{border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:12px;background:#0b0e0b;margin:8px 0}.elite{border-color:#caff5a;box-shadow:0 0 20px rgba(202,255,90,.18)}.name{font-size:24px;font-weight:1000}.meta,.reason{color:#ccc}.score{font-size:30px;color:#caff5a;font-weight:1000}.bar{height:10px;background:#222;border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,#5dff7b,#caff32,#ff8a00)}
</style>
''', unsafe_allow_html=True)


def hero():
    st.markdown('<div class="header"><div class="title">MASTER MLB BLENDER</div><div class="sub">FEED • BLEND • SURVIVE</div></div>', unsafe_allow_html=True)


def blender_machine(names, state="READY"):
    if not names:
        names = ["FEED PLAYERS"]
    chips = ''.join([f'<span class="chip">{str(n)}</span>' for n in names[:8]])
    st.markdown(f'<div class="machine"><div class="jar">{chips}</div><div class="state">{state}</div></div>', unsafe_allow_html=True)


def fmt(x):
    try:
        return f"{float(x):.1f}"
    except Exception:
        return str(x or "")


def card(r):
    score = float(r.get("score", 0) or 0)
    elite = " elite" if score >= 78 else ""
    return f'''
<div class="card{elite}">
  <div class="name">{r.get('player','')}</div>
  <div class="score">{fmt(score)} / 100</div>
  <div class="bar"><div class="fill" style="width:{max(0,min(100,score))}%"></div></div>
  <div class="meta">{r.get('game','')} • {r.get('team','')} vs {r.get('pitcher','')}</div>
  <div class="meta">{r.get('official_core_role','')} • {r.get('archetype','')}</div>
  <div class="reason">{r.get('gate_path','')}</div>
</div>'''


def tickets_view(results, key_prefix='tickets'):
    if not results:
        return
    st.subheader("CORE 3")
    core = results.get("core", pd.DataFrame())
    if core is None or core.empty:
        st.info("No clean Core 3 yet.")
    else:
        for _, r in core.head(3).iterrows():
            st.markdown(card(r), unsafe_allow_html=True)
        st.download_button("Download core.csv", csv_bytes(core), f"core_{key_prefix}.csv", "text/csv", key=f"core_{key_prefix}")

    st.subheader("ALT 3")
    alt = results.get("alt", pd.DataFrame())
    if alt is None or alt.empty:
        st.caption("No Alt 3 yet.")
    else:
        for _, r in alt.head(3).iterrows():
            st.markdown(card(r), unsafe_allow_html=True)
        st.download_button("Download alt.csv", csv_bytes(alt), f"alt_{key_prefix}.csv", "text/csv", key=f"alt_{key_prefix}")

    st.subheader("CHAOS 3")
    chaos = results.get("chaos", pd.DataFrame())
    if chaos is None or chaos.empty:
        st.caption("No Chaos 3 yet.")
    else:
        for _, r in chaos.head(3).iterrows():
            st.markdown(card(r), unsafe_allow_html=True)
        st.download_button("Download chaos.csv", csv_bytes(chaos), f"chaos_{key_prefix}.csv", "text/csv", key=f"chaos_{key_prefix}")


def game_board_view(results):
    st.subheader("Game Board")
    owners = results.get("owners", pd.DataFrame()) if results else pd.DataFrame()
    survivors = results.get("survivors", pd.DataFrame()) if results else pd.DataFrame()
    if owners is not None and not owners.empty:
        st.dataframe(owners, use_container_width=True, hide_index=True)
    elif survivors is not None and not survivors.empty:
        st.dataframe(survivors, use_container_width=True, hide_index=True)
    else:
        st.caption("No game board yet.")


def recap_view(results):
    if not results:
        return
    if st.button("RUN RECAP CHECK", use_container_width=True):
        recap = run_recap_check(results)
        st.write(recap.get("meta", {}))
        df = recap.get("recap", pd.DataFrame())
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
