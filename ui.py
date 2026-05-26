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


# === V150 UI OVERRIDE: SHOW CORE SLOT + PASSES/CUTS ===
def _v150_df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def tickets_view(results, key_prefix="tickets_v150"):
    st.markdown("## 🎟️ Tickets — V150 TRUE BLENDER")
    window=st.selectbox("Slate window",["Full slate","Early","Late"],key=f"{key_prefix}_window")
    for label,key in [("CORE 3 — Primary / Adjacent / WHO", "core"), ("ALT 3", "alt"), ("CHAOS / WHO 3", "chaos")]:
        st.markdown(f"### {label}")
        df=_v150_df(results.get(key) if isinstance(results,dict) else None).copy()
        if window!="Full slate" and "slate_window" in df.columns:
            labels=set(df["slate_window"].dropna().astype(str).str.lower().unique())
            if labels & {"early","late"}:
                df=df[df["slate_window"].astype(str).str.lower()==window.lower()]
        if df.empty:
            st.info("No Blender-qualified legs in this bucket.")
        else:
            cols=[c for c in ["core_slot","player","game_key","team","pitcher","official_core_role","blender_score","support_score","archetype","final_reason"] if c in df.columns]
            st.dataframe(df[cols],use_container_width=True,hide_index=True)
            for _,r in df.iterrows():
                card(r)
            st.download_button(f"Download {label}",csv_bytes(df),f"{key}_v150.csv","text/csv",key=f"{key_prefix}_{key}_{window}_{len(df)}")

def game_board_grid_view(results, key_prefix="gb_v150"):
    st.markdown("## 🧩 GAME BOARD — V150 PASSES + CUTS")
    if not isinstance(results,dict):
        st.info("Run the Blender first."); return
    meta=results.get("meta",{}) or {}
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Owners",meta.get("owners_locked",0)); c2.metric("Pass Rows",meta.get("passed_rows",0)); c3.metric("Cuts",meta.get("cut_rows",0)); c4.metric("Core",meta.get("core_count",0))
    if meta.get("message"): st.info(meta["message"])
    owners=_v150_df(results.get("owners")); core=_v150_df(results.get("core")); cuts=_v150_df(results.get("cuts")); board=_v150_df(results.get("game_board")); roles=_v150_df(results.get("role_board")); surv=_v150_df(results.get("survivors"))
    st.markdown("### Structured Core")
    if core.empty: st.warning("No Core built.")
    else:
        cols=[c for c in ["core_slot","player","game_key","team","pitcher","official_core_role","blender_score","support_score","archetype"] if c in core.columns]
        st.dataframe(core[cols],use_container_width=True,hide_index=True)
    st.markdown("### Locked Owners")
    if owners.empty: st.warning("No owners locked.")
    else:
        cols=[c for c in ["game_key","player","team","pitcher","official_core_role","blender_score","support_score","archetype","final_reason"] if c in owners.columns]
        st.dataframe(owners[cols],use_container_width=True,hide_index=True)
    with st.expander("PASS rows / survivors", expanded=True):
        pass_df=surv[surv["blender_eligible"]==True] if "blender_eligible" in surv.columns else pd.DataFrame()
        cols=[c for c in ["game_key","player","team","pitcher","official_core_role","archetype","blender_score","support_score","final_reason"] if c in pass_df.columns]
        st.dataframe(pass_df[cols],use_container_width=True,hide_index=True)
    with st.expander("CUT rows with reasons", expanded=True):
        cols=[c for c in ["game_key","player","team","pitcher","archetype","blender_score","final_reason","gate_trace_json"] if c in cuts.columns]
        st.dataframe(cuts[cols],use_container_width=True,hide_index=True)
    with st.expander("Every gate trace — pass/cut", expanded=False):
        st.dataframe(board,use_container_width=True,hide_index=True)
    with st.expander("Role memory — Primary / Adjacent / WHO", expanded=False):
        st.dataframe(roles,use_container_width=True,hide_index=True)



# ============================================================
# V151 FINAL UI OVERRIDE
# ============================================================

def _v151_ui_df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def _v151_bucket(results, key):
    if not isinstance(results, dict):
        return pd.DataFrame()
    df = _v151_ui_df(results.get(key)).copy()
    owners = _v151_ui_df(results.get("owners")).copy()
    if key == "core" and df.empty and not owners.empty:
        df = owners.head(3).copy()
        df["ticket_role"] = "CORE"
    return df

def tickets_view(results, key_prefix="tickets_v151"):
    st.markdown("## 🎟️ Tickets — TRUE BLENDER V151")
    window = st.selectbox("Slate window", ["Full slate","Early","Late"], key=f"{key_prefix}_window")
    if window != "Full slate":
        st.caption("Window filter only applies when official Early/Late labels exist.")
    for label,key in [("CORE 3 — Primary / Adjacent / WHO", "core"), ("ALT 3", "alt"), ("CHAOS / WHO 3", "chaos")]:
        st.markdown(f"### {label}")
        df = _v151_bucket(results, key)
        if window != "Full slate" and "slate_window" in df.columns:
            labels = set(df["slate_window"].dropna().astype(str).str.lower().unique())
            if labels & {"early","late"}:
                df = df[df["slate_window"].astype(str).str.lower()==window.lower()]
        if df.empty:
            st.info("No Blender-qualified legs in this bucket.")
        else:
            cols=[c for c in ["core_slot","player","game_key","game_time_et","team","pitcher","official_core_role","archetype","blender_score","support_score","final_reason"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
            for _, r in df.iterrows():
                card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{key}_v151.csv", "text/csv", key=f"{key_prefix}_{key}_{window}_{len(df)}")

def game_board_grid_view(results, key_prefix="gb_v151"):
    st.markdown("## 🧩 GAME BOARD — TRUE BLENDER V151")
    if not isinstance(results, dict):
        st.info("Run the Blender first.")
        return
    meta = results.get("meta", {}) or {}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Owners", meta.get("owners_locked",0))
    c2.metric("Pass Rows", meta.get("passed_rows",0))
    c3.metric("Cuts", meta.get("cut_rows",0))
    c4.metric("Core", meta.get("core_count",0))
    if meta.get("message"): st.info(meta["message"])

    core=_v151_ui_df(results.get("core")); owners=_v151_ui_df(results.get("owners")); surv=_v151_ui_df(results.get("survivors")); cuts=_v151_ui_df(results.get("cuts")); board=_v151_ui_df(results.get("game_board")); roles=_v151_ui_df(results.get("role_board"))
    st.markdown("### Structured Core")
    if core.empty:
        st.warning("No Core built.")
    else:
        cols=[c for c in ["core_slot","player","game_key","team","pitcher","official_core_role","blender_score","support_score","archetype"] if c in core.columns]
        st.dataframe(core[cols], use_container_width=True, hide_index=True)
    st.markdown("### Locked Owners")
    if owners.empty:
        st.warning("No owners locked.")
    else:
        cols=[c for c in ["game_key","player","team","pitcher","official_core_role","blender_score","support_score","archetype","final_reason"] if c in owners.columns]
        st.dataframe(owners[cols], use_container_width=True, hide_index=True)
    with st.expander("PASS rows / survivors", expanded=True):
        pass_df = surv[surv["blender_eligible"]==True] if "blender_eligible" in surv.columns else pd.DataFrame()
        cols=[c for c in ["game_key","player","team","pitcher","official_core_role","archetype","blender_score","support_score","final_reason"] if c in pass_df.columns]
        st.dataframe(pass_df[cols], use_container_width=True, hide_index=True)
    with st.expander("CUT rows with reasons", expanded=True):
        cols=[c for c in ["game_key","player","team","pitcher","archetype","blender_score","final_reason","gate_trace_json"] if c in cuts.columns]
        st.dataframe(cuts[cols], use_container_width=True, hide_index=True)
    with st.expander("Every gate trace — pass/cut", expanded=False):
        st.dataframe(board, use_container_width=True, hide_index=True)
    with st.expander("Role memory — Primary / Adjacent / WHO", expanded=False):
        st.dataframe(roles, use_container_width=True, hide_index=True)


# ============================================================
# V152 VISUAL REPAIR UI — no ugly wide tables for main output
# ============================================================

def _v152_df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def _v152_small_card(r, subtitle_extra=""):
    name = str(r.get("player",""))
    role = str(r.get("core_slot", r.get("official_core_role","")))
    arch = str(r.get("archetype",""))
    score = r.get("blender_score", r.get("score", 0))
    game = str(r.get("game_key",""))
    time = str(r.get("game_time_et",""))
    pitcher = str(r.get("pitcher",""))
    st.markdown(f"""
<div class="ticket-card">
  <div>
    <h3>{name}</h3>
    <p><b>{role}</b> · {arch}</p>
    <p>{game}{(" · " + time) if time else ""}</p>
    <p>vs {pitcher}</p>
    {("<p>"+subtitle_extra+"</p>") if subtitle_extra else ""}
  </div>
  <div class="score-pill">{score}%</div>
</div>
""", unsafe_allow_html=True)

def tickets_view(results, key_prefix="tickets_v152"):
    st.markdown("## 🎟️ Tickets — TRUE BLENDER")
    window = st.selectbox("Slate window", ["Full slate","Early","Late"], key=f"{key_prefix}_window")
    if window != "Full slate":
        st.caption("Official Early/Late filter only applies when slate labels exist.")
    for label, key in [("CORE 3 — PRIMARY / ADJACENT / WHO", "core"), ("ALT 3", "alt"), ("CHAOS / WHO 3", "chaos")]:
        st.markdown(f"### {label}")
        df = _v152_df(results.get(key) if isinstance(results, dict) else None).copy()
        if window != "Full slate" and "slate_window" in df.columns:
            labels = set(df["slate_window"].dropna().astype(str).str.lower().unique())
            if labels & {"early","late"}:
                df = df[df["slate_window"].astype(str).str.lower() == window.lower()]
        if df.empty:
            st.info("No Blender-qualified legs in this bucket.")
        else:
            for _, r in df.iterrows():
                _v152_small_card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{key}_v152.csv", "text/csv", key=f"{key_prefix}_{key}_{window}_{len(df)}")

def game_board_grid_view(results, key_prefix="gb_v152"):
    st.markdown("## 🧩 GAME BOARD — TRUE BLENDER")
    if not isinstance(results, dict):
        st.info("Run the Blender first.")
        return

    meta = results.get("meta", {}) or {}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Owners", meta.get("owners_locked",0))
    c2.metric("Pass Rows", meta.get("passed_rows",0))
    c3.metric("Cuts", meta.get("cut_rows",0))
    c4.metric("Core", meta.get("core_count",0))
    if meta.get("message"):
        st.info(meta["message"])

    core = _v152_df(results.get("core"))
    owners = _v152_df(results.get("owners"))
    survivors = _v152_df(results.get("survivors"))
    cuts = _v152_df(results.get("cuts"))
    board = _v152_df(results.get("game_board"))
    roles = _v152_df(results.get("role_board"))

    st.markdown("### Structured Core")
    if core.empty:
        st.warning("No Core built.")
    else:
        for _, r in core.iterrows():
            _v152_small_card(r)

    st.markdown("### Locked Owners")
    if owners.empty:
        st.warning("No owners locked.")
    else:
        for _, r in owners.head(25).iterrows():
            _v152_small_card(r)

    st.markdown("### PASS rows / survivors")
    pass_df = survivors[survivors["blender_eligible"] == True] if "blender_eligible" in survivors.columns else pd.DataFrame()
    if pass_df.empty:
        st.info("No pass rows.")
    else:
        for _, r in pass_df.head(35).iterrows():
            _v152_small_card(r, subtitle_extra=str(r.get("final_reason","")))

    st.markdown("### CUT rows / reasons")
    if cuts.empty:
        st.info("No cuts.")
    else:
        for _, r in cuts.head(35).iterrows():
            _v152_small_card(r, subtitle_extra=str(r.get("final_reason","")))

    with st.expander("Every gate trace — pass/cut", expanded=True):
        cols = [c for c in ["game_key","player","role","step","gate","result","score","max_score","reason","blender_score"] if c in board.columns]
        st.dataframe(board[cols] if cols else board, use_container_width=True, hide_index=True)
    with st.expander("Role memory — Primary / Adjacent / WHO", expanded=True):
        st.dataframe(roles, use_container_width=True, hide_index=True)



# ============================================================
# V154 GAME BOARD PATH UI
# Turns Game Board into board-game progression, not spreadsheet.
# ============================================================

def _v153_df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def _v153_gate_badge(label, result, reason="", score=None):
    color = "#b7ff3c" if str(result).upper() == "PASS" else "#ff5b61"
    bg = "rgba(183,255,60,.12)" if str(result).upper() == "PASS" else "rgba(255,91,97,.13)"
    score_txt = f" · {score}" if score not in [None, ""] else ""
    return f"""
    <div style="
      display:inline-block;
      min-width:96px;
      max-width:150px;
      padding:10px 12px;
      margin:6px 6px 6px 0;
      border:1px solid {color};
      border-radius:18px;
      background:{bg};
      vertical-align:top;
      font-size:13px;
      line-height:1.25;
    ">
      <b>{label}</b><br>
      <span style="color:{color};font-weight:800;">{result}{score_txt}</span><br>
      <span style="opacity:.72;">{reason[:64]}</span>
    </div>
    """

def _v153_player_path(player, rows, owner_row=None):
    rows = rows.sort_values("step") if "step" in rows.columns else rows
    score = ""
    role = ""
    game = ""
    pitcher = ""
    if owner_row is not None and not owner_row.empty:
        r = owner_row.iloc[0]
        score = r.get("blender_score", r.get("score", ""))
        role = r.get("official_core_role", "")
        game = r.get("game_key", "")
        pitcher = r.get("pitcher", "")
    else:
        first = rows.iloc[0]
        score = first.get("blender_score", "")
        role = first.get("role", "")
        game = first.get("game_key", "")
    status = "SURVIVED" if str(role).upper() not in ["CUT", "NO PICK", "NO PLAY"] else "CUT"
    status_color = "#b7ff3c" if status == "SURVIVED" else "#ff5b61"
    gates_html = ""
    for _, gr in rows.iterrows():
        gate_name = str(gr.get("gate","Gate"))
        gate_name = gate_name.replace(" / ","/")
        if len(gate_name) > 18:
            gate_name = gate_name[:18] + "…"
        gates_html += _v153_gate_badge(
            gate_name,
            gr.get("result", gr.get("verdict","")),
            str(gr.get("reason","")),
            gr.get("score","")
        )
    st.markdown(f"""
<div style="
  border:1px solid rgba(245,234,216,.18);
  border-radius:28px;
  padding:18px;
  margin:16px 0;
  background:linear-gradient(135deg, rgba(255,255,255,.045), rgba(255,255,255,.015));
">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
    <div>
      <h3 style="margin:0 0 6px 0;">{player}</h3>
      <div style="opacity:.85;font-size:15px;">{role} · {game}</div>
      <div style="opacity:.65;font-size:14px;">vs {pitcher}</div>
    </div>
    <div style="
      border:1px solid {status_color};
      color:{status_color};
      background:rgba(183,255,60,.08);
      padding:12px 14px;
      border-radius:18px;
      font-weight:900;
      white-space:nowrap;
    ">{status}<br>{score}%</div>
  </div>
  <div style="margin-top:14px;overflow-x:auto;white-space:nowrap;padding-bottom:4px;">
    {gates_html}
  </div>
</div>
""", unsafe_allow_html=True)

def game_board_grid_view(results, key_prefix="gb_v153_path"):
    st.markdown("## 🧩 GAME BOARD — BLENDER PATH")
    if not isinstance(results, dict):
        st.info("Run the Blender first.")
        return

    meta = results.get("meta", {}) or {}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Owners", meta.get("owners_locked",0))
    c2.metric("Pass Rows", meta.get("passed_rows",0))
    c3.metric("Cuts", meta.get("cut_rows",0))
    c4.metric("Core", meta.get("core_count",0))
    if meta.get("message"):
        st.info(meta["message"])

    core = _v153_df(results.get("core"))
    owners = _v153_df(results.get("owners"))
    board = _v153_df(results.get("game_board"))
    survivors = _v153_df(results.get("survivors"))
    cuts = _v153_df(results.get("cuts"))
    roles = _v153_df(results.get("role_board"))

    st.markdown("### 🎯 Structured Core Path")
    if core.empty:
        st.warning("No Core built.")
    else:
        for _, r in core.iterrows():
            _v152_small_card(r) if "_v152_small_card" in globals() else card(r)

    st.markdown("### 🏁 Owners by Game")
    if owners.empty:
        st.warning("No owners locked.")
    else:
        for _, r in owners.head(25).iterrows():
            _v152_small_card(r) if "_v152_small_card" in globals() else card(r)

    st.markdown("### 🧱 Gate Path Board")
    if board.empty or "player" not in board.columns:
        st.info("No gate trace loaded.")
    else:
        view_mode = st.radio("Board view", ["Owners first", "Cuts first", "All"], horizontal=True, key=f"{key_prefix}_view")
        owner_players = set(owners["player"].astype(str)) if not owners.empty and "player" in owners.columns else set()
        cut_players = set(cuts["player"].astype(str)) if not cuts.empty and "player" in cuts.columns else set()

        if view_mode == "Owners first":
            players = list(owners["player"].astype(str).head(20)) if not owners.empty else list(board["player"].astype(str).unique()[:20])
        elif view_mode == "Cuts first":
            players = list(cuts["player"].astype(str).head(20)) if not cuts.empty else list(board["player"].astype(str).unique()[:20])
        else:
            players = list(board["player"].astype(str).drop_duplicates().head(35))

        for p in players:
            rows = board[board["player"].astype(str) == str(p)].copy()
            owner_row = owners[owners["player"].astype(str) == str(p)].copy() if not owners.empty and "player" in owners.columns else pd.DataFrame()
            _v153_player_path(p, rows, owner_row)

    st.markdown("### ✅ Pass Rows")
    pass_df = survivors[survivors["blender_eligible"] == True] if "blender_eligible" in survivors.columns else pd.DataFrame()
    if pass_df.empty:
        st.info("No pass rows.")
    else:
        for _, r in pass_df.head(25).iterrows():
            _v152_small_card(r, subtitle_extra=str(r.get("final_reason",""))) if "_v152_small_card" in globals() else card(r)

    st.markdown("### ❌ Cut Rows")
    if cuts.empty:
        st.info("No cuts.")
    else:
        for _, r in cuts.head(25).iterrows():
            _v152_small_card(r, subtitle_extra=str(r.get("final_reason",""))) if "_v152_small_card" in globals() else card(r)

    with st.expander("Raw gate trace table", expanded=False):
        cols = [c for c in ["game_key","player","role","step","gate","result","score","max_score","reason","blender_score"] if c in board.columns]
        st.dataframe(board[cols] if cols else board, use_container_width=True, hide_index=True)
    with st.expander("Raw role memory", expanded=False):
        st.dataframe(roles, use_container_width=True, hide_index=True)
