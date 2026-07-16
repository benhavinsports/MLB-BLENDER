def run_audit(survivors: list[dict], logs: list[dict]) -> dict:
    executed={item.get("gate") for item in logs}
    required={0,1,2,3,4,5,6,7,8,9,10,10.5,11,12,13,14,15,16,17,18}
    issues=[]
    if not required.issubset(executed): issues.append("MISSING_GATE_EXECUTION")
    if not survivors: issues.append("NO_SURVIVOR")
    return {"passed":not issues,"issues":issues}
