def audit_summary(logs):
    if logs is None or logs.empty:
        return "No audit log."
    return logs.to_csv(index=False)
