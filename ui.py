import pandas as pd
import streamlit as st
from engine import csv_bytes


def inject_css():
    st.markdown("""
<style>
.stApp{background:#050505;color:#f5eadc;}
.big-title{font-size:52px;font-weight:900;line-height:.95;letter-spacing:1px;margin:18px 0 26px 0;}
.card{border:1px solid #2f2f2f;border-radius:18px;padding:18px;margin:12px 0;background:#0d0d0f;}
.score{float:right;border:1px solid #a7ff3d;border-radius:16px;padding:12px 14px;color:#eaffcf;background:#182405;font-weight:800;}
button[kind="primary"], .stButton button{border-radius:28px!important;min-height:58px;background:linear-gradient(90deg,#b6ff3e,#00f59c,#ffa51e)!important;color:#050505!important;font-weight:800!important;border:0!important;}
[data-testid="stMetricValue"]{font-size:48px;}
</style>
""", unsafe_allow_html=True)


def hero():
    st.markdown('<div class="big-title">THE<br><span style="color:#b7ff32">BLENDER</span><br>MACHINE</div>', unsafe_allow_html=True)


def blender_visual():
    st.markdown("### Feed Data")


def _df(x): return x if isinstance(x,pd.DataFrame) else pd.DataFrame()


def card(r):
    name = r.get("player", "")
    role = r.get("official_core_role", r.get("ticket_role", ""))
    game = r.get("game_key", r.get("game", ""))
    pitcher = r.get("pitcher", "")
    score = r.get("blender_score", r.get("score", 0))
    arch = r.get("archetype", "")
    time = r.get("game_time_et", "")
    st.markdown(f"""
<div class="card">
  <div class="score">{score}%</div>
  <div style="font-size:22px;font-weight:900">{name}</div>
  <div style="opacity:.9;font-weight:700">{role} · {arch}</div>
  <div style="opacity:.82">{game} {('· ' + time) if time else ''}</div>
  <div style="opacity:.72">vs {pitcher}</div>
</div>
""", unsafe_allow_html=True)


def _ticket_bucket(results, bucket):
    df = _df(results.get(bucket) if isinstance(results,dict) else None).copy()
    owners = _df(results.get("owners") if isinstance(results,dict) else None).copy()
    if df.empty and not owners.empty:
        owners = owners.drop_duplicates(["player"], keep="first") if "player" in owners.columns else owners
        if bucket == "core": df = owners.head(3).copy()
        elif bucket == "alt": df = owners.iloc[3:6].copy()
        else:
            df = owners[owners.get("official_core_role","").astype(str).eq("WHO")].head(3).copy() if "official_core_role" in owners.columns else pd.DataFrame()
            if df.empty: df = owners.iloc[6:9].copy() if len(owners)>6 else owners.tail(min(3,len(owners))).copy()
    return df


def run_ticket_view(results, bucket="core", window="Full slate"):
    df = _ticket_bucket(results,bucket).copy()
    if df.empty: return df
    if window != "Full slate" and "slate_window" in df.columns:
        labels=set(df["slate_window"].dropna().astype(str).str.lower().unique())
        if labels & {"early","late"}:
            df = df[df["slate_window"].astype(str).str.lower()==window.lower()]
    if "player" in df.columns: df=df.drop_duplicates(["player"],keep="first")
    return df


def tickets_view(results, key_prefix="tickets"):
    st.markdown("## 🎟️ Tickets")
    window=st.selectbox("Slate window",["Full slate","Early","Late"],key=f"{key_prefix}_window")
    for label,key in [("CORE 3","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"### {label}")
        df=run_ticket_view(results,key,window)
        if df.empty: st.info("No Blender-qualified legs in this window.")
        else:
            for _,r in df.iterrows(): card(r)
            st.download_button(f"Download {label}",csv_bytes(df),f"{label.lower().replace(' ','_')}.csv","text/csv",key=f"{key_prefix}_{key}_{window}_{len(df)}")


def game_board_grid_view(results, key_prefix="gb"):
    st.markdown("## 🧩 GAME BOARD — TRUE ENGINE")
    if not isinstance(results,dict): st.info("Run the Blender first."); return
    meta=results.get("meta",{}) or {}
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Rows",meta.get("input_rows",0)); c2.metric("Games",meta.get("games",0)); c3.metric("Owners",meta.get("owners_locked",0)); c4.metric("Core",meta.get("core_count",0))
    if meta.get("message"): st.info(meta["message"])
    owners=_df(results.get("owners"))
    if not owners.empty:
        st.markdown("### Locked Owners")
        for _,r in owners.head(30).iterrows(): card(r)
    else: st.warning("No locked owners.")
    with st.expander("Role Outcome Memory", expanded=False): st.dataframe(_df(results.get("role_board")),use_container_width=True,hide_index=True)
    with st.expander("True Gate Trace", expanded=False): st.dataframe(_df(results.get("game_board")),use_container_width=True,hide_index=True)
    with st.expander("Full Survivor Audit", expanded=False):
        s=_df(results.get("survivors")); cols=[c for c in ["game_key","player","team","pitcher","official_core_role","archetype","blender_eligible","metric_count","blender_score","support_score","final_reason"] if c in s.columns]
        st.dataframe(s[cols],use_container_width=True,hide_index=True)


# === TRUE BLENDER PASS/CUT BOARD V149 ===
def _v149_df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def tickets_view(results, key_prefix="tickets_v149"):
    st.markdown("## 🎟️ Tickets — TRUE BLENDER")
    window = st.selectbox("Slate window", ["Full slate","Early","Late"], key=f"{key_prefix}_window")
    for label,key in [("CORE 3 — structured", "core"), ("ALT 3", "alt"), ("CHAOS / WHO 3", "chaos")]:
        st.markdown(f"### {label}")
        df=_v149_df(results.get(key) if isinstance(results,dict) else None).copy()
        if window!="Full slate" and "slate_window" in df.columns:
            labels=set(df["slate_window"].dropna().astype(str).str.lower().unique())
            if labels & {"early","late"}:
                df=df[df["slate_window"].astype(str).str.lower()==window.lower()]
        if df.empty:
            st.info("No Blender-qualified legs in this bucket.")
        else:
            for _,r in df.iterrows():
                card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{key}_v149.csv", "text/csv", key=f"{key_prefix}_{key}_{window}_{len(df)}")

def game_board_grid_view(results, key_prefix="gb_v149"):
    st.markdown("## 🧩 GAME BOARD — PASSES + CUTS")
    if not isinstance(results,dict):
        st.info("Run the Blender first."); return
    meta=results.get("meta",{}) or {}
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Owners", meta.get("owners_locked",0))
    c2.metric("Pass Rows", meta.get("passed_rows",0))
    c3.metric("Cuts", meta.get("cut_rows",0))
    c4.metric("Core", meta.get("core_count",0))
    if meta.get("message"): st.info(meta["message"])
    owners=_v149_df(results.get("owners")); cuts=_v149_df(results.get("cuts")); board=_v149_df(results.get("game_board")); roles=_v149_df(results.get("role_board")); surv=_v149_df(results.get("survivors"))
    st.markdown("### Locked Owners")
    if owners.empty: st.warning("No owners locked.")
    else:
        for _,r in owners.head(30).iterrows(): card(r)
    with st.expander("PASS rows / survivors", expanded=True):
        pass_df=surv[surv["blender_eligible"]==True] if "blender_eligible" in surv.columns else pd.DataFrame()
        cols=[c for c in ["game_key","player","team","pitcher","official_core_role","archetype","blender_score","support_score","final_reason"] if c in pass_df.columns]
        st.dataframe(pass_df[cols], use_container_width=True, hide_index=True)
    with st.expander("CUT rows with reasons", expanded=True):
        cols=[c for c in ["game_key","player","team","pitcher","archetype","blender_score","final_reason","gate_trace_json"] if c in cuts.columns]
        st.dataframe(cuts[cols], use_container_width=True, hide_index=True)
    with st.expander("Every gate trace — pass/cut", expanded=False):
        st.dataframe(board, use_container_width=True, hide_index=True)
    with st.expander("Role memory — Primary / Adjacent / WHO", expanded=False):
        st.dataframe(roles, use_container_width=True, hide_index=True)
