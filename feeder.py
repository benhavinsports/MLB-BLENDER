
import io, re
import pandas as pd

TEAM_NAMES = [
"Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox","Cincinnati Reds",
"Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals","Los Angeles Angels","Los Angeles Dodgers",
"Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets","New York Yankees","Athletics","Oakland Athletics","Philadelphia Phillies",
"Pittsburgh Pirates","San Diego Padres","San Francisco Giants","Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers",
"Toronto Blue Jays","Washington Nationals"]
METRICS=["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge"]

def _to_num(x):
    if x is None: return None
    try:
        if pd.isna(x): return None
    except Exception: pass
    s=str(x).replace("%","").replace(",","").strip()
    if s=="" or s.lower() in {"nan","none","-","—","null"}: return None
    m=re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None

def _likely_player(s):
    s=str(s or "").strip()
    low=s.lower()
    if len(s)<3 or len(s.split())>5: return False
    bad=["http","page ","mlbstartool","projected","lineup slot","star roll","today","tomorrow","recap","filter","advanced",
         "low effort","moderate","fresh","elevated","disengaged","alert","warm","hot","cold","cond","line","park edge",
         "best","home","away","fav","unfav","neutral","neU".lower(),"hpi","dmg","hr/pa","thunderstorms","cloudy","rain"]
    if any(b in low for b in bad): return False
    for t in TEAM_NAMES:
        if low==t.lower(): return False
    if re.search(r"\d", s): return False
    return bool(re.match(r"^[A-Za-zÀ-ÿ\.\'\-\s]+$", s))

def _extract_pdf_text(data, max_pages=120):
    text=""; layers=[]
    try:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data))
        for i,p in enumerate(reader.pages[:max_pages]):
            text += f"\n__PAGE__ {i+1}\n" + (p.extract_text() or "")
        layers.append({"layer":"pypdf_text","pages":min(len(reader.pages),max_pages),"chars":len(text)})
    except Exception as e:
        layers.append({"layer":"pypdf_error","error":str(e)[:250]})
    return text,layers

def _clean_lines(text):
    return [re.sub(r"\s+"," ",l).strip() for l in str(text).splitlines() if re.sub(r"\s+"," ",l).strip()]

def _team_header(line):
    # Parsed text often joins CARDINALSPROJECTED
    m=re.match(r"^([A-Z .]+?)(?:\s*)PROJECTED\s+vs\.\s+(.+?)\s*~", line)
    if not m: return None
    raw=re.sub(r"\s+"," ",m.group(1).strip()).title()
    # fix no-space common names by contains
    team=next((t for t in TEAM_NAMES if raw.lower()==t.lower()), raw)
    pitcher=m.group(2).strip()
    return team,pitcher

def _weak_slots(line):
    m=re.match(r"^(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s+(.+)$", line)
    if not m: return None
    return m.group(1).strip().title(), ",".join(re.findall(r"#(\d+)", m.group(2)))

def _is_rank_line(s):
    return bool(re.match(r"^[1-9]$", str(s).strip()))

def _find_next_handed(lines, i):
    if i+1 < len(lines) and lines[i+1] in {"L","R"}:
        return lines[i+1], i+2
    if i+1 < len(lines) and re.match(r"^⇄?[LR]$", lines[i+1]):
        return lines[i+1].replace("⇄",""), i+2
    # Some names include switch char with hand in same line
    m=re.search(r"\s⇄?([LR])$", lines[i])
    if m:
        return m.group(1), i+1
    return "", i+1

def _extract_block_metrics(block):
    blob=" ".join(block)
    # Lineup slot
    mslot=re.search(r"\b([1-9])(?:st|nd|rd|th)\b", blob)
    lineup_slot=float(mslot.group(1)) if mslot else None
    # Pull/star percent proxy
    mpull=re.search(r"(\d+(?:\.\d+)?)%✦", blob)
    pull=float(mpull.group(1)) if mpull else None
    # Line/sweet
    mline=re.search(r"LINE\s*[↑↓]?\s*(\d+(?:\.\d+)?)%", blob)
    sweet=float(mline.group(1)) if mline else None
    # Cond/hard proxy
    mcond=re.search(r"COND\s*[↑↓]?\s*(\d+(?:\.\d+)?)%", blob)
    hard=float(mcond.group(1)) if mcond else None
    # Pitch edge
    pedges=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+(?:4-Seam|Change|Cutter|Sinker|Sweeper|Slider|Curve|Splitter)", blob)
    pitch_edge=float(pedges[0]) if pedges else None
    # HR/PA
    mhr=re.search(r"(\d+(?:\.\d+)?)%\s+HR/PA", blob)
    hrpa=float(mhr.group(1)) if mhr else None
    # DMG and HPI from local pattern
    mdmg=re.search(r"(\d+(?:\.\d+)?)\s+DMG", blob)
    dmg=float(mdmg.group(1)) if mdmg else None
    hpi=None
    if mdmg:
        before=blob[:mdmg.start()]
        nums=re.findall(r"\b(\d{2,3})\b", before[-80:])
        if nums: hpi=float(nums[-1])
    if hpi is None:
        mh=re.search(r"HPI\s*\+?\s*(\d{2,3})", blob)
        if mh: hpi=float(mh.group(1))
    tags=[]
    for tag in ["Platoon","Rakes RHP","Eats LHP","Weak Slot","Laser","ALERT","HOT","WARM","COLD"]:
        if re.search(re.escape(tag), blob, re.I): tags.append(tag)
    effort=None
    meff=re.search(r"(?:Low Effort|Moderate|Fresh|Elevated|Disengaged|High)\s+(\d{1,3})", blob)
    if meff: effort=float(meff.group(1))
    # proxies needed by engine
    barrel = min(18.0,max(3.0,dmg*6.5)) if dmg is not None else (min(18.0,max(3.0,hrpa*2.0)) if hrpa is not None else None)
    if hard is None and hpi is not None: hard=min(60.0,max(25.0,hpi*.85))
    if sweet is None and pull is not None: sweet=min(38.0,max(10.0,pull*.9))
    return {
        "lineup_slot":lineup_slot,"pull_pct":pull,"sweet_spot_pct":sweet,"barrel_pct":barrel,"hard_hit_pct":hard,
        "dmg":dmg,"hr_pa":hrpa,"hpi":hpi,"pitch_edge":pitch_edge,"hr_alert":"ALERT" in tags,"tags":", ".join(tags),"effort":effort
    }

def _parse_startool_text(text):
    lines=_clean_lines(text)
    rows=[]; page=""; team=""; pitcher=""; game=""; pitcher_weak={}
    i=0
    while i < len(lines):
        line=lines[i]
        if line.startswith("__PAGE__"):
            page=line.replace("__PAGE__","").strip(); i+=1; continue
        h=_team_header(line)
        if h:
            team,pitcher=h; game=f"{team} vs {pitcher}"; i+=1; continue
        w=_weak_slots(line)
        if w:
            pitcher_weak[w[0]]=w[1]; i+=1; continue

        # Card start can be rank line followed by player line OR just player line at page break.
        player=""
        start_i=i
        if _is_rank_line(line) and i+1 < len(lines) and _likely_player(lines[i+1]):
            player=lines[i+1].strip()
            hand, after_name = _find_next_handed(lines, i+1)
            start_i=i
        elif _likely_player(line):
            hand, after_name = _find_next_handed(lines, i)
            # require nearby card signal
            near=" ".join(lines[i:i+14])
            sig=sum([("HR/PA" in near),("DMG" in near),("★★★★★" in near or "˒˒" in near), bool(re.search(r"\b(?:1st|2nd|3rd|[4-9]th|1[0-9]th)\b",near))])
            if sig>=2:
                player=line.strip()
                start_i=i
        if not player or not team:
            i+=1; continue

        # block until next rank+player or next team header/page, capped
        j=after_name if 'after_name' in locals() else i+1
        end=min(len(lines), start_i+28)
        k=j
        while k < end:
            if k>start_i and (lines[k].startswith("__PAGE__") or _team_header(lines[k]) or _weak_slots(lines[k])):
                break
            if k>start_i+3 and _is_rank_line(lines[k]) and k+1 < len(lines) and _likely_player(lines[k+1]):
                break
            k+=1
        block=lines[start_i:k]
        metrics=_extract_block_metrics(block)
        row={"page":page,"source_layer":"startool_sequential_parser","parse_note":"rank_player_card_block","player":player,"handedness":hand,
             "team":team,"pitcher":pitcher,"game":game,"weak_slots":pitcher_weak.get(pitcher.title(),"")}
        row.update(metrics)
        rows.append(row)
        i=max(k, i+1)

    df=pd.DataFrame(rows)
    if not df.empty:
        df["_metric_count"]=df[METRICS].notna().sum(axis=1)
        df["ingestion_confidence"]=(df["_metric_count"]/len(METRICS)).clip(0,1)
        df["needs_recovery"]=df["_metric_count"]<4
        df=df[df["player"].apply(_likely_player)].copy()
        df=df.sort_values(["_metric_count","ingestion_confidence"],ascending=False)
        df=df.drop_duplicates(subset=["player","team","pitcher"],keep="first").reset_index(drop=True)
    return df

def _read_table(filename,data):
    name=filename.lower()
    if name.endswith(".csv"): return pd.read_csv(io.BytesIO(data))
    if name.endswith((".xlsx",".xls")): return pd.read_excel(io.BytesIO(data))
    return pd.DataFrame()

def read_feed(filename,data):
    audit={"filename":filename,"bytes":len(data) if data else 0,"parser":"v104_startool_sequential","layers":[],"rows":0,"columns":[]}
    try:
        name=filename.lower()
        if name.endswith((".csv",".xlsx",".xls")):
            df=_read_table(filename,data)
            audit["layers"].append({"layer":"table_file","rows":len(df)})
        elif name.endswith(".pdf"):
            text,layers=_extract_pdf_text(data)
            audit["layers"].extend(layers)
            df=_parse_startool_text(text)
        else:
            text=data.decode("utf-8",errors="ignore") if isinstance(data,(bytes,bytearray)) else str(data)
            df=_parse_startool_text(text)
        audit["rows"]=len(df); audit["columns"]=list(df.columns)
        audit["players_sample"]=df["player"].head(20).tolist() if not df.empty and "player" in df else []
        return df,audit
    except Exception as e:
        audit["error"]=str(e)
        return pd.DataFrame(),audit


# -------------------- v145 PRODUCTION FEEDER API --------------------
# app.py imports read_feed. Keep this public function stable.

def read_feed(filename=None, data=None):
    """
    Stable feeder entrypoint used by app.py.
    Returns (df, audit).
    Accepts uploaded filename + bytes, or falls back to existing parser functions if present.
    """
    import pandas as pd
    audit = {"source": filename or "uploaded", "ok": False, "rows": 0, "errors": []}

    try:
        # Prefer existing project parser names if they exist.
        for fn_name in ["parse_feed", "read_uploaded_feed", "load_feed", "parse_uploaded_file", "read_file"]:
            fn = globals().get(fn_name)
            if callable(fn):
                try:
                    result = fn(filename, data)
                except TypeError:
                    try:
                        result = fn(data)
                    except TypeError:
                        result = fn(filename)
                if isinstance(result, tuple) and len(result) == 2:
                    df, au = result
                    if isinstance(au, dict):
                        audit.update(au)
                else:
                    df = result
                if df is None:
                    df = pd.DataFrame()
                audit["ok"] = hasattr(df, "empty") and not df.empty
                audit["rows"] = int(len(df)) if hasattr(df, "__len__") else 0
                return df, audit

        # Built-in fallback for CSV.
        name = str(filename or "").lower()
        if name.endswith(".csv") and data is not None:
            import io
            df = pd.read_csv(io.BytesIO(data))
            audit["ok"] = not df.empty
            audit["rows"] = int(len(df))
            return df, audit

        # Built-in fallback for Excel.
        if (name.endswith(".xlsx") or name.endswith(".xls")) and data is not None:
            import io
            df = pd.read_excel(io.BytesIO(data))
            audit["ok"] = not df.empty
            audit["rows"] = int(len(df))
            return df, audit

        # PDF fallback: try existing PDF libraries if available, return rows parsed from text-like tables.
        if name.endswith(".pdf") and data is not None:
            import io
            text = ""
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text() or ""
                        text += "\n" + t
            except Exception as e:
                audit["errors"].append(f"pdfplumber unavailable/failed: {e}")

            rows = []
            if text.strip():
                # Conservative parser: keep line records so downstream app does not crash.
                for line in text.splitlines():
                    s = " ".join(line.split())
                    if not s or len(s) < 3:
                        continue
                    rows.append({"raw_line": s})
            df = pd.DataFrame(rows)
            audit["ok"] = not df.empty
            audit["rows"] = int(len(df))
            return df, audit

        return pd.DataFrame(), audit

    except Exception as e:
        audit["errors"].append(str(e))
        return pd.DataFrame(), audit



# -------------------- v146 STABLE FEEDER ENTRYPOINT --------------------
def read_feed(filename=None, data=None):
    """
    Stable app entrypoint. Returns (df, audit).
    """
    import pandas as pd
    audit = {"ok": False, "rows": 0, "source": filename or "uploaded", "errors": []}
    try:
        for fn_name in ["parse_feed", "read_uploaded_feed", "load_feed", "parse_uploaded_file", "read_file"]:
            fn = globals().get(fn_name)
            if callable(fn) and fn_name != "read_feed":
                try:
                    result = fn(filename, data)
                except TypeError:
                    try:
                        result = fn(data)
                    except TypeError:
                        result = fn(filename)
                if isinstance(result, tuple) and len(result) == 2:
                    df, au = result
                    if isinstance(au, dict):
                        audit.update(au)
                else:
                    df = result
                if df is None:
                    df = pd.DataFrame()
                audit["ok"] = hasattr(df, "empty") and not df.empty
                audit["rows"] = int(len(df)) if hasattr(df, "__len__") else 0
                return df, audit

        name = str(filename or "").lower()
        if data is not None and name.endswith(".csv"):
            import io
            df = pd.read_csv(io.BytesIO(data))
            audit["ok"] = not df.empty
            audit["rows"] = int(len(df))
            return df, audit

        if data is not None and (name.endswith(".xlsx") or name.endswith(".xls")):
            import io
            df = pd.read_excel(io.BytesIO(data))
            audit["ok"] = not df.empty
            audit["rows"] = int(len(df))
            return df, audit

        if data is not None and name.endswith(".pdf"):
            import io
            rows = []
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text() or ""
                        for line in text.splitlines():
                            s = " ".join(line.split())
                            if s:
                                rows.append({"raw_line": s})
            except Exception as e:
                audit["errors"].append(str(e))
            df = pd.DataFrame(rows)
            audit["ok"] = not df.empty
            audit["rows"] = int(len(df))
            return df, audit

        return pd.DataFrame(), audit
    except Exception as e:
        audit["errors"].append(str(e))
        return pd.DataFrame(), audit


# -------------------- v147 STRUCTURED FEED REPAIR --------------------
def read_feed(filename=None, data=None):
    import io, re
    import pandas as pd
    import numpy as np
    audit = {"ok": False, "rows": 0, "source": filename or "uploaded", "mode": "v147_structured", "errors": []}
    name = str(filename or "").lower()

    def clean(s):
        return re.sub(r"\s+", " ", str(s or "").replace("’", "'")).strip()

    def norm(df):
        if df is None: return pd.DataFrame()
        out = df.copy()
        out.columns = [clean(c).lower().replace(" ", "_").replace("%","pct").replace("/","_") for c in out.columns]
        aliases = {"opponent_pitcher":"pitcher","pitcher_matchup":"pitcher","hr_pct_pa":"hr_pa","hr/pa":"hr_pa","sweet":"sweet_spot_pct","sweet_spot":"sweet_spot_pct","pull":"pull_pct","barrel":"barrel_pct"}
        for a,b in aliases.items():
            if a in out.columns and b not in out.columns: out[b]=out[a]
        for c in ["team","player","pitcher"]:
            if c not in out.columns: out[c]=""
            out[c]=out[c].astype(str).map(clean)
        if "game" not in out.columns:
            out["game"]=out.apply(lambda r:f"{r.get('team','')} vs {r.get('pitcher','')}",axis=1)
        for c in ["hr_pa","dmg","hpi","line_drive_pct","cond_pct","hr_edge_pct","pitch_edge_pct","effort","sweet_spot_pct","pull_pct","barrel_pct"]:
            if c not in out.columns: out[c]=np.nan
            out[c]=pd.to_numeric(out[c],errors="coerce")
        out=out[out["player"].str.split().str.len().ge(2)]
        out=out[out["team"].str.len().gt(1)&out["pitcher"].str.len().gt(1)]
        metrics=[c for c in ["hr_pa","dmg","hpi","line_drive_pct","cond_pct","hr_edge_pct"] if c in out.columns]
        if metrics: out=out[out[metrics].notna().any(axis=1)]
        return out.drop_duplicates(subset=["team","pitcher","player"],keep="first").reset_index(drop=True)

    try:
        if data is not None and name.endswith(".csv"):
            df = norm(pd.read_csv(io.BytesIO(data)))
            audit["ok"]=not df.empty; audit["rows"]=len(df)
            return df,audit
        if data is not None and (name.endswith(".xlsx") or name.endswith(".xls")):
            df = norm(pd.read_excel(io.BytesIO(data)))
            audit["ok"]=not df.empty; audit["rows"]=len(df)
            return df,audit
        if data is not None and name.endswith(".pdf"):
            import pdfplumber
            TEAM=re.compile(r"^([A-Z][A-Z\s\.\-&]+?) PROJECTED vs\. (.+)$")
            GAME=re.compile(r"^([A-Z]{2,3}) @ ([A-Z]{2,3})$")
            TIME=re.compile(r"AWAY\s+([0-9]{1,2}:[0-9]{2}\s+[AP]M\s+ET)\s+HOME")
            PLAYER=re.compile(r"^([A-ZÀ-ÿ][A-Za-zÀ-ÿ\.'’\-]+(?:\s+[A-ZÀ-ÿ][A-Za-zÀ-ÿ\.'’\-]+){1,3})\s+(R|L|⇄R|⇄L|⇄)?(?:\s+\+\d+)?$")
            ORDER=re.compile(r"^[1-9](st|nd|rd|th)$")
            pats={"hr_pa":re.compile(r"([0-9]+(?:\.[0-9]+)?)%\s*HR/PA"),"dmg":re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*DMG"),"hpi":re.compile(r"HPI\s*([0-9]+)",re.I),"line_drive_pct":re.compile(r"LINE\s*[↑↓]?\s*([0-9]+(?:\.[0-9]+)?)%"),"cond_pct":re.compile(r"COND\s*[↑↓]?\s*([0-9]+(?:\.[0-9]+)?)%"),"hr_edge_pct":re.compile(r"([+\-][0-9]+)%\s*HR")}
            pedge=re.compile(r"([+\-][0-9]+)%\s*(4-Seam|Sinker|Splitter|Slider|Cutter|Curve|Changeup|Sweeper|Fastball)")
            effort=re.compile(r"(Low Effort|Moderate|High Effort|Disengaged|Fresh|Elevated)\s+([0-9]+)")
            bad=("Star Tool","Today's","Monday","Data refreshes","FILTER","HR#","Barrel","Line Drive","Hide","https","Page","ADVANCED","Recap","Star Roll")
            def player_line(line):
                if any(line.startswith(b) for b in bad): return None
                if any(x in line for x in ["PROJECTED","VS. LINEUP SLOT","★","HR/PA","DMG","HPI"]): return None
                m=PLAYER.match(line)
                if not m: return None
                return clean(m.group(1)),clean(m.group(2))
            def finish(b):
                if not b: return None
                text=" ".join(b["lines"]); r={k:v for k,v in b.items() if k!="lines"}
                r["raw_block"]=text; r["game"]=f"{r.get('team','')} vs {r.get('pitcher','')}"
                for col,rx in pats.items():
                    m=rx.search(text); r[col]=float(m.group(1)) if m else np.nan
                pe=pedge.findall(text); r["pitch_edge_pct"]=float(pe[-1][0]) if pe else np.nan; r["pitch_type"]=pe[-1][1] if pe else ""
                ev=effort.findall(text); r["effort"]=float(ev[0][1]) if ev else np.nan; r["sweet_spot_pct"]=float(ev[-1][1]) if len(ev)>1 else np.nan
                r["pull_pct"]=np.nan; r["barrel_pct"]=np.nan
                return r
            rows=[]; cur=None; team=pitcher=away=home=gtime=""
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for pno,page in enumerate(pdf.pages,1):
                    for line in [clean(l) for l in (page.extract_text() or "").splitlines() if clean(l)]:
                        gm=GAME.match(line)
                        if gm: away,home=gm.group(1),gm.group(2)
                        tm=TIME.search(line)
                        if tm: gtime=tm.group(1)
                        th=TEAM.match(line)
                        if th:
                            if cur:
                                rows.append(finish(cur)); cur=None
                            team,pitcher=clean(th.group(1)),clean(th.group(2)); continue
                        pl=player_line(line)
                        if pl and team and pitcher:
                            if cur: rows.append(finish(cur))
                            nm,bats=pl; cur={"game_time":gtime,"away":away,"home":home,"team":team,"player":nm,"bats":bats,"lineup_spot":"","pitcher":pitcher,"page":pno,"tags":"","lines":[line]}
                            continue
                        if cur:
                            cur["lines"].append(line)
                            if ORDER.match(line): cur["lineup_spot"]=line
                            if any(t in line for t in ["Platoon","Weak Slot","Laser","Rakes RHP","Eats LHP"]): cur["tags"]=(cur.get("tags","")+" | "+line).strip(" |")
                if cur: rows.append(finish(cur))
            df=norm(pd.DataFrame([r for r in rows if r]))
            audit["ok"]=not df.empty; audit["rows"]=len(df); audit["mode"]="pdf_hitter_rows_only"
            return df,audit
        return pd.DataFrame(),audit
    except Exception as e:
        audit["errors"].append(str(e))
        return pd.DataFrame(),audit
