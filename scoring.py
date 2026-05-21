from engine import score_row, role_type

def true_blend_score(row):
    return score_row(row)

def classify_role(row):
    return role_type(row)
