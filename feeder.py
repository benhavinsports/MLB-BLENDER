import io, pandas as pd
from normalizer import clean_df
from parser_star import parse_pdf, parse_star_text

def parse_csv(b):
    raw=pd.read_csv(io.BytesIO(b))
    if raw.shape[1]<=3:
        text="\n".join(raw.astype(str).fillna("").agg(" ".join,axis=1).tolist())
        if any(k in text for k in ["PROJECTED","DMG","HR/PA","Weak","ALERT"]):
            parsed=parse_star_text(text)
            if parsed is not None and not parsed.empty:
                return parsed,text
    return clean_df(raw), ""

def parse_xlsx(b):
    return clean_df(pd.read_excel(io.BytesIO(b))), ""

def read_file(name,b):
    n=name.lower()
    if n.endswith(".pdf"): return parse_pdf(b)
    if n.endswith(".csv"): return parse_csv(b)
    return parse_xlsx(b)
