TEAM_COLORS = {
    "red sox":"#BD3039","yankees":"#0C2340","mets":"#FF5910","dodgers":"#005A9C",
    "padres":"#2F241D","phillies":"#E81828","reds":"#C6011F","mariners":"#005C5C",
    "braves":"#CE1141","twins":"#002B5C","astros":"#EB6E1F","blue jays":"#134A8E",
    "orioles":"#DF4601","rays":"#092C5C","royals":"#004687","cubs":"#0E3386",
    "cardinals":"#C41E3A","rockies":"#33006F","angels":"#BA0021","giants":"#FD5A1E",
    "diamondbacks":"#A71930","tigers":"#0C2340","guardians":"#E50022",
    "athletics":"#003831","white sox":"#27251F","pirates":"#FDB827",
    "brewers":"#FFC52F","marlins":"#00A3E0","nationals":"#AB0003","rangers":"#003278"
}

def team_color(team):
    t = str(team).lower()
    for k, v in TEAM_COLORS.items():
        if k in t:
            return v
    return "#d9ff2f"
