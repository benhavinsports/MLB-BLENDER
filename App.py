"""
app.py

MLB Blender Machine v14
Official Detector Engine

Streamlit UI
"""

from __future__ import annotations

import traceback
from datetime import datetime

import streamlit as st

from engine import run_blender


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MLB Blender Machine v14",
    page_icon="⚾",
    layout="wide",
)

# ============================================================
# HEADER
# ============================================================

st.title("MLB Blender Machine v14")
st.caption("Official Detector Engine")

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("Controls")

    debug_mode = st.toggle(
        "Debug Trace",
        value=False,
    )

    st.markdown("---")

    st.write(
        "Deterministic elimination engine"
    )

    st.write(
        "One survivor per MLB game"
    )

# ============================================================
# SESSION STATE
# ============================================================

if "results" not in st.session_state:
    st.session_state.results = None

# ============================================================
# RUN BUTTON
# ============================================================

run_clicked = st.button(
    "RUN BLENDER",
    type="primary",
    use_container_width=True,
)

if run_clicked:

    with st.spinner(
        "Running Blender Engine..."
    ):

        try:

            results = run_blender()

            st.session_state.results = results

        except Exception as exc:

            st.error(
                f"Engine failure: {exc}"
            )

            with st.expander(
                "Stack Trace"
            ):
                st.code(
                    traceback.format_exc()
                )

# ============================================================
# RESULTS
# ============================================================

results = st.session_state.results

if results:

    st.success(
        f"Completed {len(results)} game(s)"
    )

    st.markdown("---")

    for game in results:

        matchup = game.get(
            "matchup",
            "Unknown Matchup"
        )

        if "error" in game:

            with st.container():

                st.error(matchup)

                st.code(
                    game["error"]
                )

            continue

        survivor = game["survivor"]

        with st.container():

            st.subheader(matchup)

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Survivor",
                    survivor["name"],
                )

            with col2:

                st.metric(
                    "Lineup Slot",
                    survivor.get(
                        "lineup_slot",
                        "-"
                    ),
                )

            with col3:

                st.metric(
                    "Target Side",
                    game.get(
                        "target_side",
                        "-"
                    ).upper(),
                )

            score_col1, score_col2 = st.columns(
                2
            )

            with score_col1:

                st.metric(
                    "Event Score",
                    round(
                        survivor[
                            "event_score"
                        ],
                        2,
                    ),
                )

            with score_col2:

                st.metric(
                    "Pitch Edge",
                    round(
                        survivor[
                            "pitch_edge"
                        ],
                        2,
                    ),
                )

            stat1, stat2 = st.columns(2)

            with stat1:

                st.metric(
                    "Pull %",
                    round(
                        survivor[
                            "pull_pct"
                        ],
                        2,
                    ),
                )

            with stat2:

                st.metric(
                    "Hard Hit %",
                    round(
                        survivor[
                            "hard_hit_pct"
                        ],
                        2,
                    ),
                )

            if debug_mode:

                with st.expander(
                    "G0–G18 Trace"
                ):

                    trace = game.get(
                        "trace",
                        {}
                    )

                    for gate, count in trace.items():

                        st.write(
                            f"{gate}: "
                            f"{count} survivor(s)"
                        )

            st.markdown("---")

# ============================================================
# EMPTY STATE
# ============================================================

elif not run_clicked:

    st.info(
        "Press RUN BLENDER to evaluate today's MLB slate."
    )

# ============================================================
# FOOTER
# ============================================================

st.caption(
    f"Generated: {datetime.utcnow().isoformat()} UTC"
)
