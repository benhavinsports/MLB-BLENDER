import io, re
from typing import Any
import numpy as np
import pandas as pd
import streamlit as st

APP_VERSION = "V59 PDF MONSTER FEEDER"
STANDARD_COLUMNS = ["game_id","team","opponent","player","bat_side","pitcher","pitcher_hand","slot","odds","pull_pct","hard_hit_pct","barrel_pct","launch_angle","pitch_edge","hr9_split","recent_hr_allowed","notes","source"]
OUTPUT_COLUMNS = ["bucket","rank","game_id","team","opponent","player","pitcher","archetype","status","score","fire","alert","survivor_reason","gate_log"]
PLAYER_ALIASES = {"player","player_name","name","batter","batter_name","hitter","hitter_name","pick","selection"}
ALIASES = {"tm":"team","opp":"opponent","vs":"opponent","starter":"pitcher","sp":"pitcher","probable_pitcher":"pitcher","throws":"pitcher_hand","lineup_spot":"slot","batting_order":"slot","order":"slot","pull":"pull_pct","pull_percent":"pull_pct","hardhit":"hard_hit_pct","hard_hit":"hard_hit_pct","hard_hit_percent":"hard_hit_pct","hh":"hard_hit_pct","hh_pct":"hard_hit_pct","barrel":"barrel_pct","barrel_percent":"barrel_pct","brl":"barrel_pct","brl_pct":"barrel_pct","la":"launch_angle","launch":"launch_angle","pitch_type_edge":"pitch_edge","edge":"pitch_edge","pitch_mix":"pitch_edge","hr_9":"hr9_split","hr9":"hr9_split","l_r_hr_9_hr":"hr9_split","recent_hr":"recent_hr_allowed","hr_allowed_home_or_away":"recent_hr_allowed"}

def clean_text(x: Any) -> str:
    return "" if x is None else re.sub(r"\s+"," ",str(x).replace("\u00a0"," ").replace("\t"," ")).strip()

def norm_col(c):
    c = re.sub(r"[^a-z0-9]+","_",clean_text(c).lower()).strip("_")
    return "player" if c in PLAYER_ALIASES else ALIASES.get(c,c)

def to_num(x):
    s = clean_text(x).replace("%","").replace("+","")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    try: return float(m.group(0)) if m else np.nan
    except Exception: return np.nan

def is_junk_player(x):
    s = clean_text(x); low=s.lower()
    junk=["advanced mlb performance","am page","athletics projected","projected lineup","player pool","home run","hard hit","barrel rate","launch angle","pitch edge","game board","core 3","alt 3","chaos 3","share","github","streamlit","download","upload","manage app","pitcher","team","opponent"]
    return (not s) or low in {"nan","none","null"} or len(s)<3 or len(s)>60 or any(j in low for j in junk)

def standardize_df(df, source):
    report={"source":source,"raw_rows":0,"kept_rows":0,"columns":[]}
    if df is None or df.empty: return pd.DataFrame(columns=STANDARD_COLUMNS), report
    df=df.copy(); report["raw_rows"]=len(df); df.columns=[norm_col(c) for c in df.columns]; report["columns"]=list(df.columns)
    if "player" not in df.columns:
        best=None; best_score=-1
        for c in df.columns:
            score=df[c].astype(str).head(200).map(lambda v: 0 if is_junk_player(v) else 1).sum()
            if score>best_score: best,best_score=c,score
        if best: df=df.rename(columns={best:"player"})
    for c in STANDARD_COLUMNS:
        if c not in df.columns: df[c]=""
    df["source"]=source
    for c in ["game_id","team","opponent","player","bat_side","pitcher","pitcher_hand","pitch_edge","notes","source"]: df[c]=df[c].map(clean_text)
    df=df[~df["player"].map(is_junk_player)].copy()
    for c in ["slot","odds","pull_pct","hard_hit_pct","barrel_pct","launch_angle","hr9_split","recent_hr_allowed"]: df[c]=df[c].map(to_num)
    missing=df["game_id"].eq(""); combo=(df["team"].astype(str)+" vs "+df["opponent"].astype(str)).str.strip()
    df.loc[missing,"game_id"]=combo[missing].replace(" vs ",""); df["game_id"]=df["game_id"].replace("","Unknown Game")
    empty=df["notes"].eq("")
    if empty.any(): df.loc[empty,"notes"]=df.loc[empty].astype(str).agg(" | ".join,axis=1).str[:2500]
    def first_real(s):
        for v in s:
            if clean_text(v) and clean_text(v).lower() not in {"nan","none","null"}: return v
        return ""
    def max_num(s):
        vals=[to_num(v) for v in s]; vals=[v for v in vals if not pd.isna(v)]; return max(vals) if vals else np.nan
    agg={}
    for c in STANDARD_COLUMNS:
        if c=="notes": agg[c]=lambda s:" | ".join(dict.fromkeys([clean_text(x) for x in s if clean_text(x)]))[:3500]
        elif c in ["slot","odds","pull_pct","hard_hit_pct","barrel_pct","launch_angle","hr9_split","recent_hr_allowed"]: agg[c]=max_num
        else: agg[c]=first_real
    df=df.groupby(["game_id","player"],dropna=False,as_index=False).agg(agg)[STANDARD_COLUMNS].reset_index(drop=True)
    report["kept_rows"]=len(df); return df, report

def read_table_file(f):
    raw=f.getvalue(); name=f.name.lower()
    if name.endswith('.csv'):
        for enc in ['utf-8','utf-8-sig','latin-1']:
            try: return pd.read_csv(io.BytesIO(raw), encoding=enc)
            except Exception: pass
        return pd.read_csv(io.StringIO(raw.decode('utf-8',errors='ignore')), engine='python')
    if name.endswith(('.xlsx','.xls')):
        xls=pd.ExcelFile(io.BytesIO(raw)); frames=[]
        for sh in xls.sheet_names:
            try:
                t=pd.read_excel(xls,sheet_name=sh); t['source_sheet']=sh; frames.append(t)
            except Exception: pass
        return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    if name.endswith(('.txt','.tsv')):
        text=raw.decode('utf-8',errors='ignore'); sep='\t' if '\t' in text[:1000] else None
        try: return pd.read_csv(io.StringIO(text), sep=sep, engine='python')
        except Exception: return pd.DataFrame({'raw_text':text.splitlines()})
    return pd.DataFrame()

def ocr_image_bytes(image_bytes, warnings):
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance, ImageFilter
        img=Image.open(io.BytesIO(image_bytes)).convert('RGB'); gray=ImageOps.grayscale(img)
        variants=[gray, ImageEnhance.Contrast(gray).enhance(2.2), ImageEnhance.Sharpness(ImageEnhance.Contrast(gray).enhance(2.0)).enhance(2.0), gray.filter(ImageFilter.SHARPEN)]
        texts=[]
        for v in variants:
            try:
                t=pytesseract.image_to_string(v, config='--psm 6')
                if t.strip(): texts.append(t)
            except Exception: pass
        return '\n'.join(texts)
    except Exception as e:
        warnings.append(f'OCR engine unavailable: {e}'); return ''

def extract_pdf_monster(f):
    raw=f.getvalue(); chunks=[]; warnings=[]
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for i,p in enumerate(pdf.pages):
                txt=p.extract_text(x_tolerance=1,y_tolerance=3) or ''
                if txt.strip(): chunks.append(f'--- PAGE {i+1} TEXT ---\n{txt}')
                for table in p.extract_tables() or []:
                    for row in table: chunks.append(' | '.join(clean_text(x) for x in row))
    except Exception as e: warnings.append(f'PDF table layer skipped: {e}')
    try:
        import fitz
        doc=fitz.open(stream=raw,filetype='pdf')
        for i,p in enumerate(doc):
            txt=p.get_text('text') or ''
            if txt.strip(): chunks.append(f'--- PAGE {i+1} FITZ ---\n{txt}')
    except Exception as e: warnings.append(f'PDF text layer skipped: {e}')
    try:
        import fitz
        doc=fitz.open(stream=raw,filetype='pdf')
        for i,p in enumerate(doc):
            pix=p.get_pixmap(matrix=fitz.Matrix(2.8,2.8), alpha=False)
            ocr=ocr_image_bytes(pix.tobytes('png'), warnings)
            if ocr.strip(): chunks.append(f'--- PAGE {i+1} OCR ---\n{ocr}')
    except Exception as e: warnings.append(f'PDF OCR render skipped: {e}')
    return '\n'.join(chunks), warnings

def text_to_rows(text, source):
    records=[]; current_game='Unknown Game'
    for line in [clean_text(x) for x in text.splitlines() if clean_text(x)]:
        low=line.lower()
        if any(b in low for b in ['share','github','manage app','streamlit']): continue
        gm=re.search(r'\b([A-Z]{2,3})\s*(?:@|vs\.?|VS|v)\s*([A-Z]{2,3})\b', line)
        if gm: current_game=f'{gm.group(1)} vs {gm.group(2)}'
        if not re.search(r'\d|%|\+|HR|ISO|Barrel|Pull|Hard|Ult|Dmg|HPI|Adj|Odds|Slot|4-seam|fastball|slider|sinker|curve|change|cutter', line, re.I): continue
        cells=[clean_text(x) for x in (line.split('|') if '|' in line else re.split(r'\s{2,}', line)) if clean_text(x)]
        candidates=[c for c in cells[:6] if not is_junk_player(c) and re.search(r'[A-Za-z]',c)]
        if not candidates:
            for nm in re.findall(r'\b([A-Z][a-zA-Z\'.-]+(?:\s+[A-Z][a-zA-Z\'.-]+){1,2})\b', line):
                if not is_junk_player(nm): candidates.append(nm)
        for player in dict.fromkeys(candidates[:2]):
            rec={'game_id':current_game,'player':player,'notes':line,'source':source}; nums=re.findall(r'-?\d+(?:\.\d+)?%?', line)
            if 'pull' in low and nums: rec['pull_pct']=nums[-1]
            if ('hard' in low or 'hh' in low) and nums: rec['hard_hit_pct']=nums[-1]
            if 'barrel' in low and nums: rec['barrel_pct']=nums[-1]
            if 'launch' in low and nums: rec['launch_angle']=nums[-1]
            if any(p in low for p in ['4-seam','fastball','slider','sinker','curve','change','cutter','splitter','edge']): rec['pitch_edge']=line
            if 'hr/9' in low or 'hr9' in low: rec['hr9_split']=nums[-1] if nums else ''
            if 'recent' in low and 'hr' in low: rec['recent_hr_allowed']=nums[-1] if nums else ''
            records.append(rec)
    return standardize_df(pd.DataFrame(records), source)

def feed_upload(f):
    status={'file':f.name,'mode':'','recovered_rows':0,'warnings':[],'report':{}}
    name=f.name.lower()
    try:
        if name.endswith(('.csv','.xlsx','.xls','.txt','.tsv')):
            df,rep=standardize_df(read_table_file(f), f.name); status['mode']='Table/Text Monster'; status['report']=rep
        elif name.endswith('.pdf'):
            text,w=extract_pdf_monster(f); df,rep=text_to_rows(text, f.name); status['mode']='PDF Monster: text + tables + OCR'; status['warnings']+=w; status['report']=rep
        elif name.endswith(('.png','.jpg','.jpeg','.webp')):
            w=[]; text=ocr_image_bytes(f.getvalue(), w); df,rep=text_to_rows(text, f.name); status['mode']='Screenshot/JPEG Monster OCR'; status['warnings']+=w; status['report']=rep
        else:
            df=pd.DataFrame(columns=STANDARD_COLUMNS); status['mode']='Unsupported file type'; status['warnings'].append('Use PDF, screenshot, JPG/PNG/WebP, CSV, Excel, TXT.')
    except Exception as e:
        df=pd.DataFrame(columns=STANDARD_COLUMNS); status['mode']='Safe fallback'; status['warnings'].append(str(e))
    status['recovered_rows']=len(df); return df,status

def feed_many_uploads(files):
    frames=[]; statuses=[]; raw=0
    for f in files:
        df,stt=feed_upload(f); statuses.append(stt); raw+=stt.get('recovered_rows',0)
        if df is not None and not df.empty: frames.append(df)
    if frames:
        df=pd.concat(frames,ignore_index=True); df,_=standardize_df(df,'merged monster feed')
    else: df=pd.DataFrame(columns=STANDARD_COLUMNS)
    return df, {'mode':'Monster multi-file merge','recovered_rows':len(df),'raw_recovered_rows':raw,'file_statuses':statuses,'warnings':[w for s in statuses for w in s.get('warnings',[])]}

def fnum(row,col):
    try:
        v=row.get(col,np.nan); return np.nan if pd.isna(v) else float(v)
    except Exception: return np.nan

def score_fire(score):
    if score>=90: return '🔥🔥🔥 ELITE'
    if score>=78: return '🔥🔥 STRONG'
    if score>=65: return '🔥 LIVE'
    if score>=50: return '⚠️ LEAN'
    return '🧊 DATA GAP'

def alert_text(score,status):
    if status=='CORE-ELIGIBLE' and score>=90: return "🚨 HE’S HITTING A HOME RUN TODAY 🚨"
    if status=='CORE-ELIGIBLE': return '🔥 CORE HR LOCK CANDIDATE'
    if status=='ALT-TRANSFER': return '⚡ NEXT-MAN / DECOY TRANSFER ALERT'
    if status=='CHAOS-ELIGIBLE': return '🌪️ WHO / CHAOS HR ALERT'
    return '⚠️ SURVIVED, NOT CLEAN'

def gate18(row):
    player=clean_text(row.get('player',''))
    if is_junk_player(player): return None
    notes=(clean_text(row.get('notes',''))+' '+clean_text(row.get('pitch_edge',''))).lower()
    pull,hh,barrel,la=fnum(row,'pull_pct'),fnum(row,'hard_hit_pct'),fnum(row,'barrel_pct'),fnum(row,'launch_angle')
    hr9,recent,slot,odds=fnum(row,'hr9_split'),fnum(row,'recent_hr_allowed'),fnum(row,'slot'),fnum(row,'odds')
    score=0; logs=[]
    def add(v,msg):
        nonlocal score; score+=v; logs.append(msg)
    game_id=clean_text(row.get('game_id','')) or 'Unknown Game'
    add(4,'G1 No Empty Bat: PASS'); add(5 if game_id!='Unknown Game' else -2,'G2 Game Context'); add(7,'G3 Archetype classified')
    add((14 if pull>=45 else 11 if pull>=42 else 4 if pull>=35 else -12) if not pd.isna(pull) else -4, f'G4 Pull-Air {pull}')
    add((14 if hh>=50 else 11 if hh>=45 else 3 if hh>=38 else -11) if not pd.isna(hh) else -4, f'G5 Hard-Hit {hh}')
    launch_pass=False
    if not pd.isna(la) and 12<=la<=32: add(11,f'G6 Launch Window {la}'); launch_pass=True
    elif not pd.isna(barrel) and barrel>=10: add(12,f'G6 Barrel Conversion {barrel}'); launch_pass=True
    elif not pd.isna(barrel): add(4,f'G6 Barrel support {barrel}')
    else: add(-2,'G6 Barrel/Launch missing')
    pitch_pass=any(w in notes for w in ['4-seam','fastball','slider','sinker','curve','change','cutter','splitter','edge','+','mistake'])
    add(14 if pitch_pass else -4,'G7 Pitch-Type Kill Switch')
    if not pd.isna(hr9) and hr9>0: add(min(hr9*8,14),'G8 Pitcher HR/9')
    if not pd.isna(recent) and recent>0: add(min(recent*6,12),'G9 Recent HR Allowed')
    if not pd.isna(slot): add(9 if 1<=slot<=5 else 4,f'G10 Lineup Slot {slot}')
    adjacent=any(w in notes for w in ['adjacent','decoy','secondary','behind','after','protection','next man'])
    if adjacent: add(10,'G10.5 Adjacent/Decoy')
    if any(w in notes for w in ['protection','pitch around','walk risk']): add(5,'G11 Protection/Pitch-around')
    if any(w in notes for w in ['bullpen','reliever','pen']): add(5,'G12 Bullpen Continuation')
    chaos=any(w in notes for w in ['chaos','who','value','green','blowout','wind','weather','bullpen']) or (not pd.isna(slot) and slot>=6)
    if chaos: add(8,'G13 WHO/Chaos')
    if (not pd.isna(barrel) and barrel>=10) or (not pd.isna(hh) and hh>=50): add(7,'G14 True HR Conversion')
    clean_power=(not pd.isna(pull) and pull>=42) and (not pd.isna(hh) and hh>=45)
    if clean_power and (launch_pass or pitch_pass): add(8,'G15 Event Ownership PASS')
    elif adjacent or chaos: add(4,'G15 ALT/Chaos path')
    else: add(-2,'G15 weak ownership')
    if not pd.isna(odds): add(3 if abs(odds)<=700 else 1,'G16 Market/Odds')
    finisher=clean_power and (launch_pass or pitch_pass)
    if finisher: add(10,'G17 Finisher Gate PASS')
    elif adjacent: add(5,'G17 Adjacent pass')
    elif chaos: add(4,'G17 Chaos pass')
    else: add(-3,'G17 Finisher fail')
    if finisher and pitch_pass: add(8,'G18 Final Lock CLEAN')
    elif adjacent: add(4,'G18 ALT lock')
    elif chaos: add(3,'G18 CHAOS lock')
    score=max(0,min(100,round(score,1)))
    status='CORE-ELIGIBLE' if finisher and score>=78 else 'ALT-TRANSFER' if adjacent and score>=55 else 'CHAOS-ELIGIBLE' if chaos and score>=45 else 'SURVIVED BUT NOT CLEAN'
    archetype='WHO / CHAOS' if status=='CHAOS-ELIGIBLE' else 'ADJACENT / DECOY TRANSFER' if status=='ALT-TRANSFER' else 'LANE MATCH FINISHER' if finisher else 'CLEAN POWER OWNER' if clean_power else 'RECOVERED / NEEDS DATA'
    reasons=[]
    if not pd.isna(pull) and pull>=42: reasons.append('PULL-AIR')
    if not pd.isna(hh) and hh>=45: reasons.append('HARD-HIT')
    if not pd.isna(barrel) and barrel>=10: reasons.append('BARREL')
    if launch_pass: reasons.append('LAUNCH')
    if pitch_pass: reasons.append('PITCH-KILL')
    if adjacent: reasons.append('ADJACENT')
    if chaos: reasons.append('CHAOS')
    if not reasons: reasons=['18-gate data gap']
    return {'game_id':game_id,'team':clean_text(row.get('team','')),'opponent':clean_text(row.get('opponent','')),'player':player,'pitcher':clean_text(row.get('pitcher','')),'archetype':archetype,'status':status,'score':score,'fire':score_fire(score),'alert':alert_text(score,status),'survivor_reason':' + '.join(reasons),'gate_log':' | '.join(logs)}

def choose_game_owner(group):
    priority={'CORE-ELIGIBLE':4,'ALT-TRANSFER':3,'CHAOS-ELIGIBLE':2,'SURVIVED BUT NOT CLEAN':1}
    g=group.copy(); g['priority']=g['status'].map(priority).fillna(0)
    return g.sort_values(['priority','score'],ascending=[False,False]).head(1).drop(columns=['priority'])

def run_blender(df):
    empty=pd.DataFrame(columns=OUTPUT_COLUMNS)
    if df is None or df.empty: return {'tickets':empty,'core3':empty,'alt3':empty,'chaos3':empty,'game_board':empty}
    pool=pd.DataFrame([x for _,r in df.iterrows() for x in [gate18(r)] if x])
    if pool.empty: return {'tickets':empty,'core3':empty,'alt3':empty,'chaos3':empty,'game_board':empty}
    game_board=pool.groupby('game_id',group_keys=False).apply(choose_game_owner).reset_index(drop=True).sort_values('score',ascending=False).reset_index(drop=True)
    game_board.insert(0,'rank',range(1,len(game_board)+1)); game_board.insert(0,'bucket','GAME SURVIVOR')
    core3=game_board.head(3).copy(); core3['bucket']='CORE 3'; core3['rank']=range(1,len(core3)+1)
    used=set(core3['player'].tolist()); remaining=pool[~pool['player'].isin(used)].copy()
    alt=remaining[remaining['status'].isin(['ALT-TRANSFER','CORE-ELIGIBLE'])].sort_values('score',ascending=False).head(3)
    if len(alt)<3: alt=pd.concat([alt, remaining[~remaining.index.isin(alt.index)].sort_values('score',ascending=False).head(3-len(alt))])
    alt=alt.copy(); alt.insert(0,'rank',range(1,len(alt)+1)); alt.insert(0,'bucket','ALT 3')
    used |= set(alt['player'].tolist()); chaos_pool=pool[~pool['player'].isin(used)].copy()
    chaos=chaos_pool[chaos_pool['status'].eq('CHAOS-ELIGIBLE')].sort_values('score',ascending=False).head(3)
    if len(chaos)<3: chaos=pd.concat([chaos,chaos_pool[~chaos_pool.index.isin(chaos.index)].sort_values('score',ascending=True).head(3-len(chaos))])
    chaos=chaos.copy(); chaos.insert(0,'rank',range(1,len(chaos)+1)); chaos.insert(0,'bucket','CHAOS 3')
    tickets=pd.concat([core3,alt,chaos],ignore_index=True); tickets['ticket_type']=tickets['bucket']
    return {'tickets':tickets[OUTPUT_COLUMNS+['ticket_type']],'core3':core3[OUTPUT_COLUMNS],'alt3':alt[OUTPUT_COLUMNS],'chaos3':chaos[OUTPUT_COLUMNS],'game_board':game_board[OUTPUT_COLUMNS]}

def csv_bytes(df): return df.to_csv(index=False).encode('utf-8')

def inject_css():
    st.markdown('''<style>.stApp{background:radial-gradient(circle at 20% 10%,rgba(160,255,0,.15),transparent 25%),radial-gradient(circle at 80% 80%,rgba(0,140,255,.12),transparent 25%),#030503;color:#f5fff3}[data-testid="stHeader"]{background:rgba(0,0,0,0)}.block-container{padding-top:.75rem;max-width:920px}.shell{border:1px solid rgba(93,255,122,.35);border-radius:28px;padding:18px;background:rgba(0,0,0,.55)}.title{font-size:clamp(1.7rem,5vw,2.7rem);font-weight:1000;color:#caff5a;text-align:center}.jar{height:250px;border-radius:40px 40px 90px 90px;border:3px solid rgba(176,255,70,.5);background:radial-gradient(circle at 50% 35%,rgba(210,255,60,.25),transparent 30%),rgba(0,255,120,.08);display:flex;justify-content:center;align-items:center;position:relative;overflow:hidden;margin:14px 0}.jar:before{content:"";width:170px;height:170px;border-radius:50%;border:16px solid rgba(202,255,90,.3);border-left-color:#18f5a8;border-right-color:#ff9f12;position:absolute;animation:spin 1s linear infinite}.jar:after{content:"⚾ ⚾ ⚾";position:absolute;font-size:2rem;animation:orbit 2.2s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@keyframes orbit{0%{transform:rotate(0deg) translateX(70px) rotate(0deg)}100%{transform:rotate(360deg) translateX(70px) rotate(-360deg)}}.blade{font-size:4rem;z-index:2}.ready{border:1px solid rgba(112,255,146,.36);background:rgba(0,255,90,.085);color:#92ffa8;border-radius:18px;padding:13px 16px;font-weight:900;margin-top:10px}.card{border-radius:18px;padding:14px 16px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);margin-bottom:10px}.scorebar{height:13px;background:rgba(255,255,255,.12);border-radius:999px;overflow:hidden;margin:8px 0}</style>''',unsafe_allow_html=True)

def score_bar(score):
    try: s=max(0,min(100,float(score)))
    except Exception: s=0
    return f'<div class="scorebar"><div style="height:100%;width:{s}%;background:linear-gradient(90deg,#5dff7b,#caff32,#ff8a00);"></div></div>'

def card_section(df,title):
    st.markdown(f'### {title}')
    if df is None or df.empty: st.caption('No output yet.'); return
    for _,r in df.head(3).iterrows():
        st.markdown(f'''<div class="card"><b>#{int(r.get('rank',0))} {clean_text(r.get('player',''))}</b><br><span style="color:#caff5a;font-weight:900">{clean_text(r.get('fire',''))}</span>{score_bar(r.get('score',0))}<b>{clean_text(r.get('alert',''))}</b><br><small>{clean_text(r.get('game_id',''))} — {clean_text(r.get('archetype',''))} — Score {r.get('score',0)}</small><br><small>{clean_text(r.get('survivor_reason',''))}</small></div>''',unsafe_allow_html=True)

st.set_page_config(page_title='MLB Blender',page_icon='⚾',layout='wide')
inject_css()
if 'feed_df' not in st.session_state: st.session_state.feed_df=pd.DataFrame(columns=STANDARD_COLUMNS)
if 'results' not in st.session_state: st.session_state.results=run_blender(st.session_state.feed_df)
if 'feed_status' not in st.session_state: st.session_state.feed_status={}
if 'file_count' not in st.session_state: st.session_state.file_count=0
st.markdown('<div class="shell">',unsafe_allow_html=True)
st.markdown(f'<div class="title">MASTER MLB BLENDER</div><div style="text-align:center">{APP_VERSION}</div>',unsafe_allow_html=True)
uploaded_files=st.file_uploader('Feed the monster',type=['pdf','png','jpg','jpeg','webp','csv','xlsx','xls','txt','tsv'],accept_multiple_files=True)
if uploaded_files:
    df,status=feed_many_uploads(uploaded_files); st.session_state.feed_df=df; st.session_state.feed_status=status; st.session_state.file_count=len(uploaded_files)
st.markdown('<div class="jar"><div class="blade">⚙️</div></div>',unsafe_allow_html=True)
if st.button('ENGAGE BLENDER',type='primary',use_container_width=True):
    st.session_state.results=run_blender(st.session_state.feed_df); st.success('MACHINE COMPLETE — tickets built')
rows=len(st.session_state.feed_df); raw=st.session_state.feed_status.get('raw_recovered_rows',0) if st.session_state.feed_status else 0
st.markdown(f'<div class="ready">FILES: {st.session_state.file_count} | RAW RECOVERED: {raw} | BLENDER POOL: {rows}</div>',unsafe_allow_html=True)
st.markdown('</div>',unsafe_allow_html=True)
res=st.session_state.results
card_section(res.get('core3'),'🔥 Core 3')
card_section(res.get('alt3'),'🧯 Alt 3')
card_section(res.get('chaos3'),'🌪️ Chaos 3')
with st.expander('Monster feed report',expanded=False):
    st.write(st.session_state.feed_status); st.dataframe(st.session_state.feed_df,use_container_width=True,hide_index=True)
with st.expander('Game Board — one survivor per game',expanded=False): st.dataframe(res.get('game_board'),use_container_width=True,hide_index=True)
with st.expander('Tickets / CSV downloads',expanded=False):
    st.download_button('Download tickets.csv',csv_bytes(res.get('tickets',pd.DataFrame())),'tickets.csv','text/csv')
    st.download_button('Download core.csv',csv_bytes(res.get('core3',pd.DataFrame())),'core.csv','text/csv')
    st.download_button('Download alt.csv',csv_bytes(res.get('alt3',pd.DataFrame())),'alt.csv','text/csv')
    st.download_button('Download chaos.csv',csv_bytes(res.get('chaos3',pd.DataFrame())),'chaos.csv','text/csv')
    st.dataframe(res.get('tickets'),use_container_width=True,hide_index=True)
