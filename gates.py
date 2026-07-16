from __future__ import annotations


def _log(gate, name, before, after, removed=None, note=None):
    return {"gate": gate, "name": name, "before": before, "after": after, "removed": removed or [], "note": note}


def _apply(players, gate, name, predicate, logs):
    before = len(players); kept=[]; removed=[]
    for p in players:
        passed, reason = predicate(p)
        if passed: kept.append(p)
        else: removed.append({"player":p.get("name"), "reason":reason})
    logs.append(_log(gate, name, before, len(kept), removed))
    return kept


def _metric(p, key): return p.get(key)

def run_all_gates(hitters: list[dict], game: dict, target: dict):
    logs=[]
    # Gate 0: side lock
    current=[p for p in hitters if p.get("side") == target.get("side")]
    logs.append(_log(0,"Target Side Isolation",len(hitters),len(current),note=target))
    # Gate 1: environment; only hard kill known suppression
    env=game.get("environment") or {}
    suppressed=(env.get("environment_score") is not None and env.get("environment_score") <= -3)
    current=_apply(current,1,"Environment",lambda p: (not suppressed,"heavy environment suppression"),logs)
    # Gate 2: confirmed pool already enforced
    logs.append(_log(2,"Confirmed Starter Pool",len(current),len(current)))
    # Gate 3 Pull
    current=_apply(current,3,"Pull Angle",lambda p:(p.get("pull") is None or p.get("pull")>=50,"Pull < 50"),logs)
    # Gate 4 Damage support: hard stop HH <40, otherwise strengthened damage profile
    current=_apply(current,4,"Damage Support",lambda p:(p.get("hard_hit") is None or p.get("hard_hit")>=40,"Hard Hit < 40"),logs)
    # Gate 5 pitch edge
    current=_apply(current,5,"Pitch Matchup",lambda p:(p.get("pitch_edge") is None or p.get("pitch_edge")>=0,"negative pitch edge"),logs)
    # Gate 6 slot weakness / opportunity access
    current=_apply(current,6,"Slot Weakness",lambda p:((p.get("slot") or 9)<=6,"bottom-order protected slot"),logs)
    # Gate 7 recent rhythm: pass through undefined
    current=_apply(current,7,"Recent Rhythm",lambda p:(p.get("hr_heat") is None or bool(p.get("hr_heat")),"dead recent rhythm"),logs)
    # Gate 8 conversion
    current=_apply(current,8,"Conversion",lambda p:(p.get("hr_pa") is None or p.get("hr_pa")>=.025,"HR/PA below WHO floor"),logs)
    # Gate 9 hitter environment recheck
    logs.append(_log(9,"Hitter Environment Recheck",len(current),len(current),note=env))
    # Gate 10 opportunity
    current=_apply(current,10,"Opportunity",lambda p:((p.get("slot") or 9)<=6,"insufficient projected PA"),logs)
    # Gate 10.5 is applied after ownership in core; logged here as pending
    logs.append(_log(10.5,"Decoy Transfer",len(current),len(current),note="applied after ownership"))
    # Gate 11 bullpen pass through if unknown
    logs.append(_log(11,"Bullpen Continuation",len(current),len(current)))
    # Gate 12 ownership is assigned in core
    logs.append(_log(12,"Event Ownership",len(current),len(current),note="scored after gates"))
    # Gate 13 numerology only tie-break, no elimination
    logs.append(_log(13,"Numerical Resonance",len(current),len(current),note="tie-break only"))
    # Gate 14 protection pass-through if unavailable
    current=_apply(current,14,"Lineup Protection",lambda p:(p.get("protection") is None or p.get("protection")>=0,"isolated lineup cluster"),logs)
    # Gate 15 finisher profile: must have production lane, pass through if all unavailable
    def finisher(p):
        known=[p.get("hr_pa"),p.get("iso"),p.get("fb"),p.get("damage_score")]
        if all(v is None for v in known[:3]) and not p.get("damage_score"): return True,"pass-through"
        return ((p.get("hr_pa") or 0)>=.025 and (p.get("iso") or 0)>=.150 and (p.get("damage_score") or 0)>=35),"finisher floor failed"
    current=_apply(current,15,"Finisher",finisher,logs)
    # Gate 16 reduction max two prior to ownership
    current=sorted(current,key=lambda p:(p.get("hr_model_score",0),p.get("damage_score",0)),reverse=True)[:2]
    logs.append(_log(16,"Survivor Reduction",logs[-1]["after"],len(current)))
    # Gate 17 and 18 are completed in core/final lock
    logs.append(_log(17,"Audit",len(current),len(current)))
    logs.append(_log(18,"Final Lock",len(current),len(current)))
    return current,logs
