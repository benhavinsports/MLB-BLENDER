
from __future__ import annotations
import re, io
import pandas as pd
def _clean(s): return re.sub(r"\s+"," ",str(s or "")).strip()
def _num(s):
    m=re.search(r"-?\d+(?:\.\d+)?",str(s or ""))
    return float(m.group(0)) if m else 0.0
def extract_pdf_text(uploaded_file):
    data = open(uploaded_file,"rb").read() if isinstance(uploaded_file,(str,bytes)) else uploaded_file.read()
    try:
        import fitz
        doc=fitz.open(stream=data,filetype="pdf")
        return "\n".join(p.get_text("text") for p in doc)
    except Exception:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
def _player_name(line):
    if not re.match(r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ.'’\-\s]+$", line): return False
    bad=["PROJECTED","OFFICIAL","CONFIRMED","AWAY","HOME","Page","Star Tool","HPI","ALERT","HOT","WARM","COLD"]
    return not any(b in line for b in bad)
def parse_star_tool_text(text):
    lines=[_clean(x) for x in text.splitlines() if _clean(x)]
    rows=[]; game=""; team=""; pitcher=""; weak_slots=""
    i=0
    while i < len(lines):
        line=lines[i]
        if line=="@" and i>=3 and i+2<len(lines):
            # nearest team abbreviations
            left=next((lines[k] for k in range(i-1,max(-1,i-8),-1) if re.match(r"^[A-Z]{2,3}$",lines[k])), "")
            right=next((lines[k] for k in range(i+1,min(len(lines),i+8)) if re.match(r"^[A-Z]{2,3}$",lines[k])), "")
            if left and right: game=f"{left} vs {right}"
        if i+2<len(lines) and re.match(r"^[A-Z][A-Z .'-]+$", line) and lines[i+1] in ("PROJECTED","OFFICIAL","CONFIRMED") and lines[i+2].startswith("vs. "):
            team=line.title(); pitcher=lines[i+2].replace("vs.","").strip(); weak_slots=""; i+=3; continue
        if "· VS. LINEUP SLOT Weak:" in line:
            weak_slots=",".join(re.findall(r"#?(\d)", line.split("Weak:",1)[-1]))
        if re.match(r"^\d{1,2}$", line) and i+1<len(lines) and _player_name(lines[i+1]) and team:
            rank=int(line); name=lines[i+1]; j=i+2; block=[]
            if j<len(lines) and re.match(r"^(⇄)?[LR]$", lines[j]): block.append(lines[j]); j+=1
            while j<len(lines):
                nxt=lines[j]
                if re.match(r"^\d{1,2}$",nxt) and j+1<len(lines) and _player_name(lines[j+1]): break
                if j+2<len(lines) and re.match(r"^[A-Z][A-Z .'-]+$",nxt) and lines[j+1] in ("PROJECTED","OFFICIAL","CONFIRMED") and lines[j+2].startswith("vs. "): break
                if nxt == "@" or nxt in ("AWAY","HOME") or "· VS. LINEUP SLOT Weak:" in nxt: break
                block.append(nxt); j+=1
            btxt=" ".join(block)
            slot=int(_num(re.search(r"(\d)(?:st|nd|rd|th)\b",btxt).group(1))) if re.search(r"(\d)(?:st|nd|rd|th)\b",btxt) else 0
            def grab(pat):
                m=re.search(pat,btxt); return _num(m.group(1)) if m else 0.0
            hrpa=grab(r"(\d+(?:\.\d+)?)% HR/PA"); dmg=grab(r"(\d+(?:\.\d+)?) DMG")
            cond=grab(r"COND [↑↓]? ?(\d+(?:\.\d+)?)%"); linev=grab(r"LINE [↑↓]? ?(\d+(?:\.\d+)?)%")
            hredge=grab(r"([+\-]\d+)% HR"); pitch_edge=grab(r"([+\-]\d+)% (?:4-Seam|Sinker|Cutter|Sweeper|Slider|Change|Curve|Splitter)")
            # HPI usually appears as "+ 35 1.183 DMG" or "HPI 35"; use number before DMG fallback
            hpi=grab(r"HPI\s*(\d+)") or grab(r"\+\s*(\d{2})\s+\d+(?:\.\d+)? DMG")
            vals=re.findall(r"(Low Effort|Moderate|Elevated|High|Disengaged|Fresh)\s+(\d+)", btxt)
            effort=float(vals[0][1]) if vals else 0; fatigue=float(vals[-1][1]) if len(vals)>1 else 0
            badges=" ".join([w for w in ["Platoon","Rakes RHP","Weak Slot","Laser","Park Edge","ALERT","HOT","WARM","COLD","Launch"] if w.lower() in btxt.lower()])
            rows.append(dict(rank=rank,player=name,team=team,game=game or f"{team} vs {pitcher}",pitcher=pitcher,slot=slot,hr_pa=hrpa,dmg=dmg,hpi=hpi,cond=cond,line=linev,hr_edge=hredge,pitch_edge=pitch_edge,effort=effort,fatigue=fatigue,badges=badges,weak_slots=weak_slots,raw_block=btxt[:500]))
            i=j; continue
        i+=1
    return pd.DataFrame(rows)
def parse_star_tool_pdf(uploaded_file): return parse_star_tool_text(extract_pdf_text(uploaded_file))
def load_any(uploaded_file):
    name=getattr(uploaded_file,"name",str(uploaded_file)).lower()
    if name.endswith(".pdf"): return parse_star_tool_pdf(uploaded_file)
    if name.endswith(".csv"): return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx",".xls")): return pd.read_excel(uploaded_file)
    return pd.DataFrame()
