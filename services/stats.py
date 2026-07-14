# services/stats.py

import requests

# ==========================================================
# MLB HR BLENDER vFINAL
# PLAYER CARD BUILDER
#
# This file creates ONE player object
# containing everything Blender needs.
#
# No gates live here.
# No eliminations.
# Data only.
# ==========================================================


def build_player_card(player):

    return {

        # ----------------------------------
        # Identity
        # ----------------------------------

        "id": player.get("id"),

        "name": player.get("name"),

        "team": player.get("team"),

        "slot": player.get("slot"),

        # ----------------------------------
        # Pull Profile
        # ----------------------------------

        "pull": None,

        "pull_barrel": None,

        "pua": None,

        "fb": None,

        # ----------------------------------
        # Damage
        # ----------------------------------

        "hard_hit": None,

        "barrel": None,

        "exit_velocity": None,

        "blast": None,

        "squared_up": None,

        "sweet_spot": None,

        "bat_speed": None,

        "fast_swing": None,

        # ----------------------------------
        # Production
        # ----------------------------------

        "iso": None,

        "slg": None,

        "woba": None,

        "hr_pa": None,

        # ----------------------------------
        # Blender Values
        # ----------------------------------

        "pitch_edge": None,

        "condition": None,

        "hr_heat": False,

        # ----------------------------------
        # Audit
        # ----------------------------------

        "alive": True,

        "gate_failed": None

    }


# ==========================================================
# PLACEHOLDER LOADERS
#
# Each section gets replaced with
# live data later.
# ==========================================================


def load_savant(player):

    """
    Baseball Savant

    Hard Hit
    Barrel
    EV
    Blast
    Bat Speed
    etc.
    """

    return player


def load_fangraphs(player):

    """
    ISO
    SLG
    WOBA
    HR/PA

    """

    return player


def load_pitch_matchup(player):

    """
    Pitch Edge

    Filled after pitcher
    injection.

    """

    return player


def load_recent_form(player):

    """

    Last 10 games

    HR Heat

    """

    return player


# ==========================================================
# MASTER ATTACH
# ==========================================================


def attach_stats(players):

    output = []

    for p in players:

        card = build_player_card(p)

        card = load_savant(card)

        card = load_fangraphs(card)

        card = load_pitch_matchup(card)

        card = load_recent_form(card)

        output.append(card)

    return output
