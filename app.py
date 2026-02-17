import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import unicodedata
import re

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
    """Normaliseert namen: kleine letters, geen accenten, alleen de achternaam."""
    if pd.isna(text): return ""
    text = str(text).lower()
    text = re.sub(r'^[a-z]\.\s*', '', text) # Verwijder voorletters zoals 'T. '
    # Verwijder accenten (bijv. ç -> c)
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    parts = text.split()
    return parts[-1] if parts else "" # Pak laatste deel (achternaam)

@st.cache_data(ttl=3600)
def scrape_all_pcs():
    """Haalt alle startlijsten op van PCS en slaat de volledige tekst per race op."""
    results = {}
    headers = {'User-Agent': 'Mozilla/5.0'}
    for abbr, info in RACES_CONFIG.items():
        try:
            resp = requests.get(info["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            # Pak de hele tekst van de startlijst-tabel om matching-fouten te voorkomen
            table = soup.find('div', {'class': 'startlist-wrapper'})
            results[abbr] = table.text.lower() if table else ""
        except:
            results[abbr] = ""
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
        for c in ['COB', 'HLL', 'MTN', 'SPR', 'OR']:
            df[c] = pd.to_numeric(df.get(c, 20), errors='coerce').fillna(20)
            
        return df
    except Exception as e:
        st.error(f"Fout bij inladen CSV: {e}")
        return pd.DataFrame()

# --- 3. UI & LOGICA ---
st.title("Klassiekers 2026")

df_base = load_base_data()

if df_base.empty:
    st.error("Kon de basisbestanden niet koppelen.")
else:
    with st.sidebar:
        st.header("Instellingen")
        budget = st.number_input("Budget (Euro)", value=46000000, step=500000)
        
        if st.button("🔄 Forceer PCS Update"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        w_cob = st.slider("Kassei", 0, 10, 8)
        w_hll = st.slider("Heuvel", 0, 10, 6)
        w_mtn = st.slider("Klim", 0, 10, 4)
        w_spr = st.slider("Sprint", 0, 10, 5)
        w_or  = st.slider("Eendag", 0, 10, 5)

        locked = st.multiselect("Vastzetten:", df_base['NAAM'].unique())
        excluded = st.multiselect("Uitsluiten:", df_base['NAAM'].unique())

    df = df_base.copy()

    # PCS DATA INTEGRATIE
    with st.spinner("Live startlijsten ophalen van PCS..."):
        pcs_data = scrape_all_pcs()
        for r in races_all:
            # We kijken of de achternaam van onze renner voorkomt in de tekst van de PCS pagina
            df[r] = df['MATCH_KEY'].apply(lambda x: 1 if x and x in pcs_data[r] else 0)

    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)
    st.markdown("<style>[data-testid='stDataFrame'] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); }</style>", unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["Team Samensteller", "Team Schema", "Programma & Scores", "Informatie"])

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
                st.success("Team gevonden op basis van PCS startlijsten!")
            else: st.error("Geen oplossing mogelijk.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team.sort_values('PRIJS_NUM', ascending=False)[['NAAM', 'PRIJS', 'SCORE']], hide_index=True)
            st.metric("Totaal Budget", f"€ {team['PRIJS_NUM'].sum():,.0f}")

    with t2:
        if 'team_idx' in st.session_state:
            team_sel = df.loc[st.session_state['team_idx']].sort_values('PRIJS_NUM', ascending=False).copy()
            for r in races_all: 
                team_sel[r] = team_sel[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(team_sel[['NAAM'] + races_all], hide_index=True)
            
            st.divider()
            st.subheader("Kopman Suggesties (op basis van PCS deelname)")
            kop_data = []
            race_stats = {"OHN":"COB","KBK":"SPR","SB":"HLL","PN7":"MTN","TA7":"SPR","MSR":"SPR","BDP":"SPR","E3":"COB","GW":"COB","DDV":"COB","RVV":"COB","SP":"SPR","PR":"COB","BP":"HLL","AGR":"HLL","WP":"HLL","LBL":"HLL"}
            for r in races_all:
                starters = team_sel[team_sel[r] == "✅"]
                if not starters.empty:
                    top = starters.sort_values(race_stats[r], ascending=False).head(3)['NAAM'].tolist()
                    kop_data.append({"Koers": r, "Top 3": " / ".join(top)})
            st.table(pd.DataFrame(kop_data))
        else: st.info("Maak eerst een team.")

    with t3:
        st.subheader("Marktoverzicht (Live PCS)")
        market_disp = df.sort_values('PRIJS_NUM', ascending=False).copy()
        for r in races_all:
            market_disp[r] = market_disp[r].apply(lambda x: "✅" if x == 1 else "")
        cols = ['NAAM', 'PRIJS', 'COB', 'HLL', 'SPR', 'MTN', 'OR'] + races_all
        st.dataframe(market_disp[cols], hide_index=True)

    with t4:
        st.write("Data bronnen: WielerOrakel & Live ProCyclingStats.")
