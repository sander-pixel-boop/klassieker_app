import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Scorito Optimalisator Pro", layout="wide", page_icon="🚴")

# --- 1. DATA INLADEN VAN GITHUB ---
@st.cache_data
def load_external_data():
    # We laden de bestanden in vanaf de lokale lokatie in je GitHub repo
    try:
        df_p = pd.read_csv("renners_prijzen.csv")
        df_wo = pd.read_csv("renners_stats.csv")
        
        # Schoonmaken prijzen
        df_p['Prijs_Clean'] = pd.to_numeric(df_p['Prijs'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        df_p['Match_Name'] = df_p['Naam'].str.lower().str.strip()
        
        # Schoonmaken WielerOrakel (Naam conversie)
        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower()
            return str(full_name).lower()
        
        df_wo['Match_Name'] = df_wo['Naam'].apply(convert_to_short_name)
        
        # Koppelen (Merge)
        merged = pd.merge(df_p, df_wo, on='Match_Name', how='inner', suffixes=('', '_wo'))
        return merged
    except Exception as e:
        st.error(f"Fout bij laden van CSV bestanden: {e}")
        return pd.DataFrame()

df = load_external_data()

# --- 2. STARTLIJSTEN SCRAPER ---
YEAR = "2026"
RACES = {
    "Omloop": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist",
    "Kuurne": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist",
    "Strade": f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist",
    "PN Et.7": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist",
    "TA Et.7": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist",
    "RvV": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist",
    "Roubaix": f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist",
    "LBL": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist"
}

@st.cache_data(ttl=3600)
def scrape_startlists():
    results = {}
    for race, url in RACES.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.content, 'html.parser')
            riders = [a.text.strip().lower() for a in soup.select('a[href^="rider/"]')]
            results[race] = riders
        except:
            results[race] = []
    return results

# --- 3. UI ---
st.title("🏆 Scorito Manager Pro")

if df.empty:
    st.warning("Wacht op data... Zorg dat 'renners_stats.csv' en 'renners_prijzen.csv' in je GitHub staan.")
else:
    st.write(f"Database succesvol geladen: **{len(df)} renners** met prijzen en kwaliteiten.")

    # SIDEBAR
    with st.sidebar:
        st.header("1. Instellingen")
        budget = st.number_input("Totaal Budget (€)", value=46000000, step=500000)
        
        st.header("2. Strategie")
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN - PN Et. 7)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR - TA Et. 7)", 0, 10, 5)
        w_or  = st.slider("Eendags (OR)", 0, 10, 5)

    # BEREKENING
    df['Score'] = (df['COB'] * w_cob) + (df['HLL'] * w_hll) + (df['MTN'] * w_mtn) + (df['SPR'] * w_spr) + (df['OR'] * w_or)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📊 Toprenners")
        st.dataframe(df[['Naam', 'Prijs_Clean', 'Score']].sort_values('Score', ascending=False).head(20))

    with col2:
        st.subheader("🚀 Jouw Optimale Team")
        if st.button("Bereken Team (20 renners)"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
            prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
            prob += pulp.lpSum([sel[i] for i in df.index]) == 20
            prob.solve()
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                team = df.loc[[i for i in df.index if sel[i].varValue == 1]]
                st.success(f"Team gevonden! Totaal: € {team['Prijs_Clean'].sum():,.0f}")
                st.dataframe(team[['Naam', 'Prijs_Clean', 'COB', 'HLL', 'SPR']].sort_values('Prijs_Clean', ascending=False))
            else:
                st.error("Geen oplossing mogelijk binnen budget.")

    # STARTLIJSTEN
    st.divider()
    if st.button("Check Startlijsten via PCS"):
        lists = scrape_startlists()
        for race, riders in lists.items():
            df[race] = df['Match_Name'].apply(lambda x: "✅" if any(x in r or r in x for r in riders) else "")
        st.dataframe(df[['Naam'] + list(RACES.keys())])
