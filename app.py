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

# --- 2. HULPFUNCTIES VOOR MATCHING ---

def simplify_name(text):
    """Maakt namen 'kaal': geen accenten, geen initialen, alles kleine letters."""
    if pd.isna(text): return ""
    text = str(text).lower()
    # Verwijder initialen zoals 't. ' of 'm.v.d.'
    text = re.sub(r'^[a-z]\.\s*', '', text)
    text = re.sub(r'\s[a-z]\.\s*', ' ', text)
    # Verwijder accenten (ç -> c, é -> e)
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.strip()

@st.cache_data
def load_base_data():
    try:
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python')
        
        # Kolomnamen opschonen
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]

        # Naamkolom vinden
        p_name_col = next((c for c in df_p.columns if "NAAM" in c or "NAME" in c), None)
        wo_name_col = next((c for c in df_wo.columns if "NAAM" in c or "NAME" in c), None)

        if not p_name_col or not wo_name_col:
            st.error("Kon de kolom 'Naam' niet vinden in een van de bestanden.")
            return pd.DataFrame()

        # Maak sleutels voor matching
        df_p['MATCH_KEY'] = df_p[p_name_col].apply(simplify_name)
        df_wo['MATCH_KEY'] = df_wo[wo_name_col].apply(simplify_name)
        
        # Merge op de versimpelde sleutel
        df = pd.merge(df_p, df_wo, on='MATCH_KEY', how='inner', suffixes=('', '_WO'))
        
        # Prijs opschonen
        price_col = next((c for c in df.columns if "PRIJS" in c or "PRICE" in c), None)
        df['PRIJS'] = pd.to_numeric(df[price_col].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        # Originele naam behouden voor display
        df['NAAM'] = df[p_name_col]
        
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
    st.error("Kritieke fout: Database leeg. Controleer of de namen in je CSV-bestanden exact overeenkomen.")
    st.info("Tip: Zorg dat beide CSV-bestanden een kolom 'Naam' hebben.")
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

    # Startlijsten
    if startlist_source == "Statisch (CSV)":
        try:
            df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')
            df_sl.columns = [c.strip().upper() for c in df_sl.columns]
            df_sl['MATCH_KEY'] = df_sl.iloc[:,0].apply(simplify_name) # Eerste kolom is naam
            df = pd.merge(df, df_sl.drop(columns=[df_sl.columns[0]], errors='ignore'), on='MATCH_KEY', how='left').fillna(0)
        except: st.sidebar.warning("startlijsten.csv niet gevonden.")
    else:
        with st.spinner('Live startlijsten ophalen...'):
            pcs_data = scrape_pcs()
            for abbr in races_all:
                df[abbr] = df['MATCH_KEY'].apply(lambda x: 1 if x in pcs_data[abbr] else 0)

    # Key check
    for r in races_all: 
        if r not in df.columns: df[r] = 0
        df[r] = df[r].fillna(0)

    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)
    
    st.markdown("<style>[data-testid='stDataFrame'] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); }</style>", unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["Team Samensteller", "Team Schema", "Programma volgens PCS", "Informatie"])

    with t1:
        if st.button("Genereer Optimaal Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            prob += pulp.lpSum([df['SCORE'][i] * sel[i] for i in df.index])
            prob += pulp.lpSum([df['PRIJS'][i] * sel[i] for i in df.index]) <= budget
            prob += pulp.lpSum([sel[i] for i in df.index]) == 20
            for i, row in df.iterrows():
                if row['NAAM'] in locked_riders: prob += (sel[i] == 1)
                if row['NAAM'] in excluded_riders: prob += (sel[i] == 0)
            prob.solve()
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                st.success("Team gevonden ✅")
            else: st.error("Geen oplossing mogelijk.")
        
        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team[['NAAM', 'PRIJS', 'SCORE']].sort_values('PRIJS', ascending=False), hide_index=True)

    with t2:
