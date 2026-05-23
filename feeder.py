
import io, re, math
import pandas as pd

TEAM_NAMES = ["Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox","Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals","Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets","New York Yankees","Athletics","Oakland Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres","San Francisco Giants","Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"]
TEAM_ABBR = {"ari":"Arizona Diamondbacks","atl":"Atlanta Braves","bal":"Baltimore Orioles","bos":"Boston Red Sox","chc":"Chicago Cubs","chw":"Chicago White Sox","cin":"Cincinnati Reds","cle":"Cleveland Guardians","col":"Colorado Rockies","det":"Detroit Tigers","hou":"Houston Astros","kc":"Kansas City Royals","laa":"Los Angeles Angels","lad":"Los Angeles Dodgers","mia":"Miami Marlins","mil":"Milwaukee Brewers","min":"Minnesota Twins","nym":"New York Mets","nyy":"New York Yankees","ath":"Athletics","oak":"Athletics","phi":"Philadelphia Phillies","pit":"Pittsburgh Pirates","sd":"San Diego Padres","sf":"San Francisco Giants","sea":"Seattle Mariners","stl":"St. Louis Cardinals","tb":"Tampa Bay Rays","tex":"Texas Rangers","tor":"Toronto Blue Jays","wsh":"Washington Nationals","was":"Washington Nationals"}
SCHEMA_ALIASES = {
    "player":["player","name","batter","hitter","bat"], "team":["team","tm","club"], "opponent":["opponent","opp","vs"],
    "pitcher":["pitcher","opp pitcher","opposing pitcher","probable pitcher","sp","starter"], "game":["game","matchup","teams"],
    "lineup_slot":["slot","lineup","batting order","order","bo","spot"], "pull_pct":["pull","pull%","pull pct","pull_pct","pull percent","pull air"],
    "sweet_spot_pct":["sweet","sweet%","sweet spot","sweet spot%","sweet_spot_pct","sweetspot"], "barrel_pct":["barrel","barrel%","barrel pct","barrel_pct","brl","brl%"],
    "hard_hit_pct":["hardhit","hard hit","hard-hit","hh%","hard hit%","hard_hit_pct","hardhit%","hard"], "dmg":["dmg","damage"],
    "hr_pa":["hr/pa","hr pa","hr_pa","hr rate","hrpa"], "hpi":["hpi"], "pitch_edge":["pitch edge","pitch_edge","edge","pitch","pitch type edge"],
    "weak_slots":["weak slots","weak slot","slot weakness"], "hr_alert":["hr alert","alert","hr flag"]
}
METRICS = ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge"]

def _clean_col(c): return re.sub(r"[^a-z0-9]+"," ",str(c).strip().lower()).strip()
def _to_num(x):
    if x is None: return None
    try:
        if pd.isna(x): return None
    except Exception: pass
    s=str(x).replace("%","").replace(",","").strip()
    if s=="" or s.lower() in {"nan","none","-","—","null"}: return None
    m=re.search(r"-?\d+(?:\.\d+)?",s)
    return float(m.group()) if m else None
def _likely_player(s):
    s=str(s or "").strip()
    if len(s)<3 or len(s.split())>5: return False
    if s.lower() in {"low effort","medium effort","high effort","effort","player","team","pitcher","pull","hpi","dmg","page","barrel","sweet","hard hit"}: return False
    if re.search(r"\d",s): return False
    return bool(re.match(r"^[A-Za-zÀ-ÿ\.\'\-\s]+$",s))
def _find_team(text):
    low=str(text or "").lower()
    for t in TEAM_NAMES:
        if t.lower() in low: return t
    for abbr,team in TEAM_ABBR.items():
        if re.search(rf"\b{re.escape(abbr)}\b", low): return team
    return ""
def _schema_map(headers):
    mapped={}
    clean={_clean_col(h):h for h in headers}
    for canon,aliases in SCHEMA_ALIASES.items():
        for a in aliases:
            ca=_clean_col(a)
            if ca in clean:
                mapped[clean[ca]]=canon
                break
    return mapped
def _canon_cols(df):
    if df is None or df.empty: return pd.DataFrame()
    return df.rename(columns=_schema_map(df.columns))

# 1) Multi-layer PDF/OCR extraction
def _extract_pdf_layers(data):
    layers=[]
    try:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data)); txt=""
        for i,p in enumerate(reader.pages): txt += f"\n__PAGE__ {i+1}\n" + (p.extract_text() or "")
        if txt.strip(): layers.append(("pypdf_text",txt))
    except Exception as e: layers.append(("pypdf_error",str(e)))
    try:
        import pdfplumber
        txt=""; tables=[]
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i,p in enumerate(pdf.pages):
                txt += f"\n__PAGE__ {i+1}\n" + (p.extract_text(x_tolerance=1,y_tolerance=3) or "")
                for table in (p.extract_tables() or []):
                    if table and len(table)>1: tables.append((i+1,table))
        if txt.strip(): layers.append(("pdfplumber_text",txt))
        if tables: layers.append(("pdfplumber_tables",tables))
    except Exception as e: layers.append(("pdfplumber_error",str(e)))
    try:
        import fitz
        doc=fitz.open(stream=data,filetype="pdf"); txt=""
        for i,page in enumerate(doc): txt += f"\n__PAGE__ {i+1}\n" + (page.get_text("text") or "")
        if txt.strip(): layers.append(("pymupdf_text",txt))
    except Exception as e: layers.append(("pymupdf_error",str(e)))
    try:
        import fitz, pytesseract
        from PIL import Image
        doc=fitz.open(stream=data,filetype="pdf"); txt=""
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
            img=Image.open(io.BytesIO(pix.tobytes("png")))
            txt += f"\n__PAGE__ {i+1}\n" + pytesseract.image_to_string(img)
        if txt.strip(): layers.append(("ocr_image_text",txt))
    except Exception as e: layers.append(("ocr_unavailable_or_failed",str(e)))
    return layers

# 2) Semantic table reconstruction
def _tables_to_frames(tables):
    frames=[]
    for page,table in tables:
        try:
            best_i,best_score=0,-1
            for i,row in enumerate(table[:6]):
                labels=[_clean_col(x) for x in row]
                score=sum(any(val in [_clean_col(a) for a in aliases] for aliases in SCHEMA_ALIASES.values()) for val in labels)
                if score>best_score: best_i,best_score=i,score
            headers=[str(x or f"col_{i}") for i,x in enumerate(table[best_i])]
            df=pd.DataFrame(table[best_i+1:],columns=headers); df["page"]=page; df["source_layer"]="pdfplumber_table"
            frames.append(_canon_cols(df))
        except Exception: pass
    return frames

# 3) Cross-page context memory
def _parse_lines(text, source="text"):
    rows=[]; ctx={"team":"","pitcher":"","game":"","page":""}
    for raw in str(text).splitlines():
        line=re.sub(r"\s+"," ",raw).strip()
        if not line: continue
        if line.startswith("__PAGE__"):
            ctx["page"]=line.replace("__PAGE__","").strip(); continue
        team=_find_team(line)
        if team:
            ctx["team"]=team
            if " vs " in line.lower() or "@" in line: ctx["game"]=line
        pm=re.search(r"(?:vs|versus|against)\s+([A-Z][A-Za-z\.\'\-]+(?:\s+[A-Z][A-Za-z\.\'\-]+){0,2})",line)
        if pm and len(line.split())<14: ctx["pitcher"]=pm.group(1).strip()
        nums=re.findall(r"-?\d+(?:\.\d+)?%?",line)
        if not nums: continue
        before=line.split(nums[0])[0].strip(" -|•\t:")
        before=re.sub(r"^\d+\s+","",before).strip()
        for t in TEAM_NAMES: before=before.replace(t,"").strip()
        words=before.split()
        candidates=[]
        if len(words)>=2: candidates += [" ".join(words[-2:]), " ".join(words[-3:]) if len(words)>=3 else ""]
        candidates.append(before)
        player=next((c for c in candidates if _likely_player(c)),"")
        if not player: continue
        vals=[_to_num(x) for x in nums]
        row={"source_layer":source,"page":ctx["page"],"player":player,"team":ctx["team"],"pitcher":ctx["pitcher"],"game":ctx["game"]}
        for i,m in enumerate(METRICS): row[m]=vals[i] if i<len(vals) else None
        rows.append(row)
    return pd.DataFrame(rows)

# 4) Adaptive schema detection + 5) Confidence/recovery
def _normalize(df):
    df=_canon_cols(df)
    if df is None or df.empty: return pd.DataFrame()
    if "player" not in df.columns:
        best_col,best_rate=None,0
        for c in df.columns:
            vals=df[c].dropna().astype(str).head(100)
            rate=vals.map(_likely_player).mean() if len(vals) else 0
            if rate>best_rate: best_col,best_rate=c,rate
        if best_col is not None: df=df.rename(columns={best_col:"player"})
    if "player" not in df.columns: return pd.DataFrame()
    for c in ["team","opponent","pitcher","game","weak_slots","page","source_layer"]:
        if c not in df.columns: df[c]=""
    for c in METRICS+["lineup_slot"]:
        if c not in df.columns: df[c]=None
        df[c]=df[c].apply(_to_num)
    if "hr_alert" not in df.columns: df["hr_alert"]=False
    df["player"]=df["player"].astype(str).str.strip()
    df=df[df["player"].apply(_likely_player)].copy()
    for c in ["team","opponent","pitcher","game","weak_slots","page","source_layer"]:
        df[c]=df[c].fillna("").astype(str).replace("nan","")
    df["_metric_count"]=df[METRICS].notna().sum(axis=1)
    df["ingestion_confidence"]=(df["_metric_count"]/len(METRICS)).clip(0,1)
    df["needs_recovery"]=df["_metric_count"]<3
    return df[df["_metric_count"]>=1].reset_index(drop=True)

def _dedupe(frames):
    usable=[]
    for f in frames:
        nf=_normalize(f)
        if not nf.empty: usable.append(nf)
    if not usable: return pd.DataFrame()
    df=pd.concat(usable,ignore_index=True).sort_values(["_metric_count","ingestion_confidence"],ascending=False)
    for c in ["player","team","pitcher"]:
        if c not in df.columns: df[c]=""
    return df.drop_duplicates(subset=["player","team","pitcher"],keep="first").reset_index(drop=True)

def _read_table(filename,data):
    name=filename.lower()
    if name.endswith(".csv"): return pd.read_csv(io.BytesIO(data))
    if name.endswith((".xlsx",".xls")): return pd.read_excel(io.BytesIO(data))
    return pd.DataFrame()

def read_feed(filename,data):
    audit={"filename":filename,"bytes":len(data) if data else 0,"layers":[],"raw_rows":0,"rows":0,"columns":[]}
    frames=[]
    try:
        name=filename.lower()
        if name.endswith((".csv",".xlsx",".xls")):
            raw=_read_table(filename,data); frames.append(raw); audit["layers"].append({"layer":"table_file","rows":len(raw)})
        elif name.endswith(".pdf"):
            for layer,payload in _extract_pdf_layers(data):
                if layer.endswith("_error") or layer.startswith("ocr_unavailable"):
                    audit["layers"].append({"layer":layer,"error":str(payload)[:250]}); continue
                if layer=="pdfplumber_tables":
                    tframes=_tables_to_frames(payload); frames.extend(tframes)
                    audit["layers"].append({"layer":layer,"frames":len(tframes),"rows":sum(len(x) for x in tframes) if tframes else 0})
                else:
                    parsed=_parse_lines(payload,layer); frames.append(parsed); audit["layers"].append({"layer":layer,"rows":len(parsed)})
        else:
            text=data.decode("utf-8",errors="ignore") if isinstance(data,(bytes,bytearray)) else str(data)
            parsed=_parse_lines(text,"text"); frames.append(parsed); audit["layers"].append({"layer":"text","rows":len(parsed)})
        audit["raw_rows"]=sum(len(f) for f in frames if f is not None)
        df=_dedupe(frames)
        audit["rows"]=len(df); audit["columns"]=list(df.columns)
        audit["schema"]={c:str(df[c].dtype) for c in df.columns} if not df.empty else {}
        return df,audit
    except Exception as e:
        audit["error"]=str(e)
        return pd.DataFrame(),audit
