
import io, re, os
import pandas as pd
import requests
try:
    import streamlit as st
except Exception:
    st = None
from feeder_brain import clean_df

BASE_URL = "https://mlbstartool.com"

def get_secret(name, default=""):
    if st is not None:
        try:
            if name in st.secrets:
                return st.secrets[name]
        except Exception:
            pass
    return os.getenv(name, default)

def _tables(html):
    try:
        return [t for t in pd.read_html(io.StringIO(html)) if t is not None and len(t)]
    except Exception:
        return []

def _score_table(df):
    cols=" ".join(str(c).lower() for c in df.columns)
    score=0
    for k in ["player","hitter","batter","team","pitcher","hpi","dmg","hr/pa","pull","lineup","slot","edge"]:
        if k in cols:
            score += 3
    score += min(len(df),300)/50
    return score

def _best(tables):
    if not tables:
        return pd.DataFrame()
    return sorted(tables, key=_score_table, reverse=True)[0]

def _links(html, url):
    out=[]
    for href in re.findall(r'href=["\\\']([^"\\\']+)["\\\']', html, flags=re.I):
        low=href.lower()
        if any(x in low for x in ["csv","export","download","slate","projection","data"]):
            out.append(requests.compat.urljoin(url, href))
    return list(dict.fromkeys(out))

def _form_inputs(form_html):
    inputs={}
    for tag in re.findall(r"<input\b[^>]*>", form_html, flags=re.I):
        name_m=re.search(r'name=["\\\']([^"\\\']+)["\\\']', tag, flags=re.I)
        if not name_m:
            continue
        name=name_m.group(1)
        type_m=re.search(r'type=["\\\']([^"\\\']+)["\\\']', tag, flags=re.I)
        val_m=re.search(r'value=["\\\']([^"\\\']*)["\\\']', tag, flags=re.I)
        typ=(type_m.group(1).lower() if type_m else "text")
        val=(val_m.group(1) if val_m else "")
        inputs[name]={"type":typ,"value":val}
    return inputs

def _read_url(session, url):
    r=session.get(url, timeout=30)
    r.raise_for_status()
    ctype=r.headers.get("content-type","").lower()
    if "csv" in ctype or url.lower().endswith(".csv"):
        return pd.read_csv(io.StringIO(r.text))
    if "excel" in ctype or url.lower().endswith((".xlsx",".xls")):
        return pd.read_excel(io.BytesIO(r.content))
    return _best(_tables(r.text))

def _login(session, url, user, password):
    r=session.get(url, timeout=30)
    r.raise_for_status()
    html=r.text
    forms=re.findall(r"<form\b[^>]*>.*?</form>", html, flags=re.I|re.S)
    if not forms:
        return False, r.url, "No login form found."
    for form in forms:
        inputs=_form_inputs(form)
        if not inputs:
            continue
        payload={k:v["value"] for k,v in inputs.items()}
        user_key=None
        pass_key=None
        for name,meta in inputs.items():
            lname=name.lower()
            typ=meta["type"].lower()
            if pass_key is None and (typ=="password" or "pass" in lname):
                pass_key=name
            if user_key is None and (typ in ["text","email"] or any(k in lname for k in ["user","email","login"])):
                user_key=name
        if not pass_key:
            continue
        if not user_key:
            for name,meta in inputs.items():
                typ=meta["type"].lower()
                if typ not in ["hidden","submit","button","checkbox","password"]:
                    user_key=name
                    break
        if not user_key:
            continue
        payload[user_key]=user
        payload[pass_key]=password
        action_m=re.search(r'action=["\\\']([^"\\\']+)["\\\']', form, flags=re.I)
        method_m=re.search(r'method=["\\\']([^"\\\']+)["\\\']', form, flags=re.I)
        action=action_m.group(1) if action_m else url
        method=(method_m.group(1).lower() if method_m else "post")
        post_url=requests.compat.urljoin(url, action)
        res=session.get(post_url, params=payload, timeout=30) if method=="get" else session.post(post_url, data=payload, timeout=30)
        low=res.text.lower()
        if res.status_code < 400 and not any(x in low for x in ["invalid password","incorrect","login failed"]):
            return True, res.url, "Login submitted."
    return False, url, "Could not submit login form."

def pull_star_tool():
    user=get_secret("STAR_USER","")
    password=get_secret("STAR_PASS","")
    token=get_secret("STAR_TOKEN","")
    export_url=get_secret("STAR_EXPORT_URL","")
    login_url=get_secret("STAR_LOGIN_URL",BASE_URL)

    debug={"base_url":BASE_URL,"has_user":bool(user),"has_pass":bool(password),"has_token":bool(token),"used_export_url":bool(export_url)}
    session=requests.Session()
    session.headers.update({"User-Agent":"Mozilla/5.0 BlenderMachine/42", "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})

    if export_url:
        try:
            if token:
                session.headers.update({"Authorization":f"Bearer {token}"})
            raw=_read_url(session, export_url)
            return clean_df(raw), "STAR_EXPORT_URL pulled.", debug
        except Exception as e:
            debug["export_error"]=str(e)

    if not user or not password:
        return pd.DataFrame(), "Missing STAR_USER / STAR_PASS in Streamlit Secrets.", debug

    last=""
    for url in [login_url, BASE_URL, BASE_URL.rstrip("/")+"/login", BASE_URL.rstrip("/")+"/signin", BASE_URL.rstrip("/")+"/users/sign_in", BASE_URL.rstrip("/")+"/account/login"]:
        try:
            ok, final_url, msg=_login(session,url,user,password)
            last=msg
            if not ok:
                continue
            pages=[BASE_URL, BASE_URL.rstrip()+"/dashboard", BASE_URL.rstrip()+"/mlb", BASE_URL.rstrip()+"/mlb/hr", BASE_URL.rstrip()+"/projections", BASE_URL.rstrip()+"/slate", final_url]
            all_tables=[]; found=[]
            for p in list(dict.fromkeys(pages)):
                try:
                    res=session.get(p, timeout=30)
                    if res.status_code >= 400:
                        continue
                    found += _links(res.text,p)
                    all_tables += _tables(res.text)
                except Exception:
                    pass
            for link in found[:12]:
                try:
                    raw=_read_url(session, link)
                    if raw is not None and not raw.empty:
                        all_tables.append(raw)
                except Exception:
                    pass
            raw=_best(all_tables)
            if raw is not None and not raw.empty:
                df=clean_df(raw)
                debug["tables_found"]=len(all_tables)
                debug["links_found"]=found[:12]
                if not df.empty:
                    return df, "STAR TOOL auto-pull completed.", debug
                return raw, "STAR TOOL pulled a table, but columns need mapping. Check Feeder Lab.", debug
        except Exception as e:
            last=str(e)
    return pd.DataFrame(), f"Auto-login tried but no usable table/export was found. Last status: {last}", debug
