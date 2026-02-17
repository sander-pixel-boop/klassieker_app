import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import unicodedata
import re
import time

st.set_page_config(page_title="Klassiekers 2026", layout="wide")

# --- 1. CONFIGURATIE & PCS URLS ---
YEAR = "2026"
RACES_CONFIG = {
    "OHN": {"url": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist", "stat": "COB"},
    "KBK": {"url": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist", "stat": "SPR"},
    "SB":  {"url": f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist", "stat": "HLL"},
    "PN7": {"url": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist", "stat": "MTN"},
    "TA7": {"url": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist", "stat": "SPR"},
    "MSR": {"url": f"https://www.procyclingstats.com/race/milano-sanremo/{YEAR}/startlist", "stat": "SPR"},
    "BDP": {"url": f"https://www.procyclingstats.com/race/classic-brugge-de-panne/{YEAR}/startlist", "stat": "SPR"},
    "E3":  {"url": f"https://www.procyclingstats.com/race/e3-harelbeke/{YEAR}/startlist", "stat": "COB"},
    "GW":  {"url": f"https://www.procyclingstats.com/race/gent-wevelgem/{YEAR}/startlist", "stat": "COB"},
    "DDV": {"url": f"https://www.procyclingstats.com/race/dwars-door-vlaanderen/{YEAR}/startlist", "stat": "COB"},
    "RVV": {"url": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist", "stat": "COB"},
    "SP":  {"url": f"https://www.procyclingstats.com/race/scheldeprijs/{YEAR}/startlist", "stat": "SPR"},
    "PR":  {"url": f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist", "stat": "COB"},
    "BP":  {"url": f"https://www.procyclingstats.com/race/brabantse-pijl/{YEAR}/startlist", "stat": "HLL"},
    "AGR": {"url": f"https://www.procyclingstats.com/race/amstel-gold-race/{YEAR}/startlist", "stat": "HLL"},
    "WP":  {"url": f"https://www.procyclingstats.com/race/fleche-wallonne/{YEAR}/startlist", "stat": "HLL"},
    "LBL": {"url": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist", "stat": "HLL"}
}
races_all = list(RACES_CONFIG.keys())

# --- 2. HULPFUNCTIES ---

def super_clean(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    text = re.sub(r'^[a-z]\.\s*', '', text) 
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    parts = text.split()
    return parts[-1] if parts else ""

@st.cache_data(ttl=3600)
def scrape_all_pcs():
    results = {}
    # Gebruik een realistische User-Agent
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    progress_text = st.empty()
    for i, (abbr, info) in enumerate(RACES_CONFIG.items()):
        try:
            progress_text.text(f"Laden van PCS: {abbr}...")
            resp = requests.get(info["url"], headers=headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                # We pakken de hele tekst van de rennerslijst sectie
                main_content = soup.find('div', {'class': 'page-content'})
                results[abbr] = main_content.text.lower() if main_content else ""
            else:
                results[abbr] = "BLOCKED"
            time.sleep(0.5) # Korte pauze om blokkades te voorkomen
        except:
            results[abbr] = ""
    progress_text.empty()
    return results

@st.cache_data
def load_base_data():
    try:
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python', encoding='utf-8-sig')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]
        df_p['MATCH_KEY'] = df_p['NAAM'].apply(super_clean)
        df_wo['MATCH_KEY'] = df_wo['NAAM'].apply(super_clean)
        df = pd.merge(df_p, df_wo.drop(columns=['NAAM'], errors='ignore'), on='MATCH_KEY', how='left')
        df['PRIJS_NUM'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(500000)
        return df
    except Exception as e:
        st.error(f"Fout bij inladen: {e}")
        return pd.DataFrame()

# --- 3. UI ---
st.title("Klassiekers 2026")

df_base = load_base_data()

if df_base.empty:
    st.error("Basisbestanden niet gevonden.")
else:
    with st.sidebar:
        st.header("Instellingen")
        budget = st.number_input("Budget (Euro)", value=46000000, step=500000)
        if st.button("🔄 Ververs PCS Data"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        locked = st.multiselect("Vastzetten:", df_base['NAAM'].unique())
        excluded = st.multiselect("Uitsluiten:", df_base['NAAM'].unique())

    df = df_base.copy()

    # PCS DATA OPHALEN
    pcs_raw = scrape_all_pcs()
    
    # Check of we geblokkeerd zijn
    if any(v == "BLOCKED" for v in pcs_raw.values()):
        st.warning("PCS blokkeert momenteel directe toegang. De app probeert startlijsten.csv te gebruiken.")
        try:
            df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
            df_sl.columns = [c.strip().upper() for c in df_sl.columns]
            df_sl['MATCH_KEY'] = df_sl['NAAM'].apply(super_clean)
            df = pd.merge(df, df_sl.drop(columns=['NAAM'], errors='ignore'), on='MATCH_KEY', how='left').fillna(0)
        except:
            st.error("Backup startlijsten.csv ook niet gevonden.")
    else:
        for r in races_all:
            df[r] = df['MATCH_KEY'].apply(lambda x: 1 if x and x in pcs_raw.get(r, "") else 0)

    # Berekening scores
    for c in ['COB', 'HLL', 'MTN', 'SPR', 'OR']:
        df[c] = pd.to_numeric(df.get(c, 20), errors='coerce').fillna(20)
    
    df['SCORE'] = (df['COB']*8) + (df['HLL']*6) + (df['MTN']*4) + (df['SPR']*5) + (df['OR']*5)
    st.markdown("<style>[data-testid='stDataFrame'] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); }</style>", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Team Samensteller", "Team Schema", "Programma & Scores"])

    with t1:
        if st.button("Genereer Optimaal Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            prob += pulp.lpSum([df['SCORE'][i] * sel[i] for i in df.index])
            prob += pulp.lpSum([df['PRIJS_NUM'][i] * sel[i] for i in df.index]) <= budget
            prob += pulp.lpSum([sel[i] for i in df.index]) == 20
            for i, row in df.iterrows():
                if row['NAAM'] in locked: prob += (sel[i] == 1)
                if row['NAAM'] in excluded: prob += (sel[i] == 0)
            prob.solve()
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                st.success("Team gevonden!")
            else: st.error("Geen oplossing mogelijk.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team.sort_values('PRIJS_NUM', ascending=False)[['NAAM', 'PRIJS', 'SCORE']], hide_index=True)

    with t2:
        if 'team_idx' in st.session_state:
            team_sel = df.loc[st.session_state['team_idx']].sort_values('PRIJS_NUM', ascending=False).copy()
            for r in races_all: team_sel[r] = team_sel[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(team_sel[['NAAM'] + races_all], hide_index=True)
            
            st.divider()
            st.subheader("Kopman Suggesties")
            kop_data = []
            race_stats = {"OHN":"COB","KBK":"SPR","SB":"HLL","PN7":"MTN","TA7":"SPR","MSR":"SPR","BDP":"SPR","E3":"COB","GW":"COB","DDV":"COB","RVV":"COB","SP":"SPR","PR":"COB","BP":"HLL","AGR":"HLL","WP":"HLL","LBL":"HLL"}
            for r in races_all:
                starters = team_sel[team_sel[r] == "✅"]
                if not starters.empty:
                    top = starters.sort_values(race_stats[r], ascending=False).head(3)['NAAM'].tolist()
                    kop_data.append({"Koers": r, "Top 3": " / ".join(top)})
            st.table(pd.DataFrame(kop_data))

    with t3:
        st.subheader("Marktoverzicht")
        market_disp = df.sort_values('PRIJS_NUM', ascending=False).copy()
        for r in races_all: market_disp[r] = market_disp[r].apply(lambda x: "✅" if x == 1 else "")
        st.dataframe(market_disp[['NAAM', 'PRIJS', 'COB', 'HLL', 'SPR', 'MTN', 'OR'] + races_all], hide_index=True)
