import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import unicodedata
import re

st.set_page_config(page_title="Klassiekers 2026", layout="wide")

# --- 1. CONFIGURATIE ---
YEAR = "2026"
RACES_CONFIG = {
    "OHN": {"url": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist", "full": "Omloop Het Nieuwsblad", "stat": "COB"},
    "KBK": {"url": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist", "full": "Kuurne-Brussel-Kuurne", "stat": "SPR"},
    "SB":  {"url": f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist", "full": "Strade Bianche", "stat": "HLL"},
    "PN7": {"url": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist", "full": "Parijs-Nice Etappe 7", "stat": "MTN"},
    "TA7": {"url": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist", "full": "Tirreno-Adriatico Etappe 7", "stat": "SPR"},
    "MSR": {"url": f"https://www.procyclingstats.com/race/milano-sanremo/{YEAR}/startlist", "full": "Milano-Sanremo", "stat": "SPR"},
    "BDP": {"url": f"https://www.procyclingstats.com/race/classic-brugge-de-panne/{YEAR}/startlist", "full": "Brugge-De Panne", "stat": "SPR"},
    "E3":  {"url": f"https://www.procyclingstats.com/race/e3-harelbeke/{YEAR}/startlist", "full": "E3 Saxo Classic", "stat": "COB"},
    "GW":  {"url": f"https://www.procyclingstats.com/race/gent-wevelgem/{YEAR}/startlist", "full": "Gent-Wevelgem", "stat": "COB"},
    "DDV": {"url": f"https://www.procyclingstats.com/race/dwars-door-vlaanderen/{YEAR}/startlist", "full": "Dwars door Vlaanderen", "stat": "COB"},
    "RVV": {"url": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist", "full": "Ronde van Vlaanderen", "stat": "COB"},
    "SP":  {"url": f"https://www.procyclingstats.com/race/scheldeprijs/{YEAR}/startlist", "full": "Scheldeprijs", "stat": "SPR"},
    "PR":  {"url": f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist", "full": "Parijs-Roubaix", "stat": "COB"},
    "BP":  {"url": f"https://www.procyclingstats.com/race/brabantse-pijl/{YEAR}/startlist", "full": "Brabantse Pijl", "stat": "HLL"},
    "AGR": {"url": f"https://www.procyclingstats.com/race/amstel-gold-race/{YEAR}/startlist", "full": "Amstel Gold Race", "stat": "HLL"},
    "WP":  {"url": f"https://www.procyclingstats.com/race/fleche-wallonne/{YEAR}/startlist", "full": "Waalse Pijl", "stat": "HLL"},
    "LBL": {"url": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist", "full": "Luik-Bastenaken-Luik", "stat": "HLL"}
}
races_all = list(RACES_CONFIG.keys())

# --- 2. HULPFUNCTIES ---

def simplify_name(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    text = re.sub(r'^[a-z]\.\s*', '', text)
    text = re.sub(r'\s[a-z]\.\s*', ' ', text)
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.strip()

@st.cache_data
def load_base_data():
    try:
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python')
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]
        df_p['MATCH_KEY'] = df_p['NAAM'].apply(simplify_name)
        df_wo['MATCH_KEY'] = df_wo['NAAM'].apply(simplify_name)
        df = pd.merge(df_p, df_wo, on='MATCH_KEY', how='inner', suffixes=('', '_WO'))
        df['PRIJS'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        df['NAAM'] = df['NAAM'] # Behoud originele naam uit prijzenbestand
        return df
    except Exception as e:
        st.error(f"Fout bij laden: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def scrape_pcs():
    results = {}
    for abbr, info in RACES_CONFIG.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(info["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            riders = [simplify_name(a.text) for a in soup.find_all('a', href=True) if 'rider/' in a['href']]
            results[abbr] = riders
        except:
            results[abbr] = []
    return results

# --- 3. UI ---
st.title("Klassiekers 2026")

df_base = load_base_data()

if df_base.empty:
    st.error("Kritieke fout: Database leeg. Controleer of de namen in je CSV-bestanden overeenkomen.")
else:
    with st.sidebar:
        st.header("Strategie en Filters")
        budget = st.number_input("Budget (Euro)", value=46000000, step=500000)
        st.divider()
        startlist_source = st.radio("Bron Startlijsten:", ["Statisch (CSV)", "Live (PCS)"])
        st.divider()
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        w_or  = st.slider("Eendags kwaliteit (OR)", 0, 10, 5)
        st.divider()
        locked_riders = st.multiselect("Vastzetten (Locks):", df_base['NAAM'].unique())
        excluded_riders = st.multiselect("Uitsluiten (Excludes):", df_base['NAAM'].unique())

    df = df_base.copy()

    if startlist_source == "Statisch (CSV)":
        try:
            df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')
            df_sl.columns = [c.strip().upper() for c in df_sl.columns]
            df_sl['MATCH_KEY'] = df_sl['NAAM'].apply(simplify_name)
            df = pd.merge(df, df_sl.drop(columns=['NAAM']), on='MATCH_KEY', how='left').fillna(
