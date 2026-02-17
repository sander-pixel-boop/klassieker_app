import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import time
import io

st.set_page_config(page_title="Scorito Manager Pro", layout="wide", page_icon="🚴")

# --- 1. DATA INLADEN ---
@st.cache_data
def load_external_data():
    try:
        # Gebruik sep=None om automatisch te detecteren of het , of ; is
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python', on_bad_lines='skip')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python', on_bad_lines='skip')
        
        df_p.columns = df_p.columns.str.strip()
        df_wo.columns = df_wo.columns.str.strip()

        df_p['Prijs_Clean'] = pd.to_numeric(df_p['Prijs'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        df_p['Match_Name'] = df_p['Naam'].str.lower().str.strip()
        
        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                last_name = ' '.join(parts[1:]).replace('"', '').replace("'", "")
                first_letter = parts[0][0]
                return f"{first_letter}. {last_name}".lower()
            return str(full_name).lower()
        
        df_wo['Match_Name'] = df_wo['Naam'].apply(convert_to_short_name)
        
        # Merge op Match_Name
        merged = pd.merge(df_p, df_wo, on='Match_Name', how='inner', suffixes=('', '_wo'))
        return merged
    except Exception as e:
        st.error(f"Fout bij laden van data: {e}")
        return pd.DataFrame()

df = load_external_data()

# --- 2. PCS SCRAPER ---
YEAR = "2026"
RACES = {
    "Omloop": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist",
    "Kuurne": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist",
    "Strade": f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist",
    "PN Et.7": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist",
    "TA Et.7": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist",
    "MSR": f"https://www.procyclingstats.com/race/milano-sanremo/{YEAR}/startlist",
    "E3": f"https://www.procyclingstats.com/race/e3-harelbeke/{YEAR}/startlist",
    "Gent-W": f"https://www.procyclingstats.com/race/gent-wevelgem/{YEAR}/startlist",
    "DDV": f"https://www.procyclingstats.com/race/dwars-door-vlaanderen/{YEAR}/startlist",
    "RvV": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist",
    "Schelde": f"https://www.procyclingstats.com/race/scheldeprijs/{YEAR}/startlist",
    "Roubaix": f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist",
    "Brabantse": f"https://www.procyclingstats.com/race/brabantse-pijl/{YEAR}/startlist",
    "Amstel": f"https://www.procyclingstats.com/race/amstel-gold-race/{YEAR}/startlist",
    "Waalse Pijl": f"https://www.procyclingstats.com/race/fleche-wallonne/{YEAR}/startlist",
    "LBL": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist",
    "Eschborn": f"https://www.procyclingstats.com/race/eschborn-frankfurt/{YEAR}/startlist"
}

@st.cache_data(ttl=3600)
def scrape_startlists():
    results = {}
    for race, url in RACES.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            # Zoek renner namen in de PCS tabel
            riders = [a.text.strip().lower() for a in soup.select('a[href^="rider/"]')]
            results[race] = riders
        except:
            results[race] = []
    return results

# --- 3. UI STRUCTUUR ---
st.title("🏆 Scorito Klassieker Master 2026")

if df.empty:
    st.warning("Data kon niet worden geladen. Controleer je CSV bestanden op GitHub.")
else:
    # Maak tabbladen
    tab_solver, tab_programma = st.tabs(["🚀 Team Samensteller", "📅 Wedstrijdschema"])

    with st.sidebar:
        st.header("⚙️ Instellingen")
        budget = st.number_input("Budget (€)", value=46000000, step=500000)
        
        st.divider()
        st.subheader("🎯 Strategie Gewicht")
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN / PN Et.7)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR / TA Et.7)", 0, 10, 5)
        w_or  = st.slider("Eendags kwaliteit (OR)", 0, 10, 5)
        
        st.divider()
        update_btn = st.button("🔄 Ververs PCS Startlijsten")

    # Score berekenen
    df['Score'] = (df['COB'] * w_cob) + (df['HLL'] * w_hll) + (df['MTN'] * w_mtn) + (df['SPR'] * w_spr) + (df['OR'] * w_or)

    # --- TAB 1: SAMENSTELLER ---
    with tab_solver:
        col_list, col_team = st.columns([1, 1])
        
        with col_list:
            st.subheader("Toprenners voor jouw strategie")
            st.dataframe(df[['Naam', 'Prijs_Clean', 'Score']].sort_values('Score', ascending=False).head(25))

        with col_team:
            st.subheader("Optimalisatie")
            if st.button("Genereer Optimaal Team (20 renners)"):
                prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
                sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
                
                prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
                prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
                prob += pulp.lpSum([sel[i] for i in df.index]) == 20
                
                prob.solve()
                
                if pulp.LpStatus[prob.status] == 'Optimal':
                    st.session_state['selected_team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                    st.success(f"Team gevonden! Kosten: € {df.loc[st.session_state['selected_team_idx'], 'Prijs_Clean'].sum():,.0f}")
                else:
                    st.error("Geen oplossing mogelijk binnen budget.")

            if 'selected_team_idx' in st.session_state:
                team = df.loc[st.session_state['selected_team_idx']]
                st.dataframe(team[['Naam', 'Prijs_Clean', 'COB', 'HLL', 'SPR']].sort_values('Prijs_Clean', ascending=False))
            else:
                st.info("Klik op de knop om een team te genereren.")

    # --- TAB 2: WEDSTRIJDSCHEMA ---
    with tab_programma:
        st.subheader("Gedetailleerd Wedstrijdprogramma")
        
        if 'selected_team_idx' not in st.session_state:
            st.warning("Stel eerst een team samen in het tabblad 'Team Samensteller'.")
        else:
            if update_btn or 'pcs_lists' not in st.session_state:
                with st.spinner("Startlijsten ophalen..."):
                    st.session_state['pcs_lists'] = scrape_startlists()
            
            team = df.loc[st.session_state['selected_team_idx']].copy()
            
            # Matrix bouwen
            for race, riders in st.session_state['pcs_lists'].items():
                # We checken of de Match_Name of de achternaam voorkomt in de PCS lijst
                team[race] = team['Match_Name'].apply(lambda x: "✅" if any(x in r or r.split('-')[-1] in x for r in riders) else "")
            
            # Tabel tonen
            st.write("Vinkjes zijn gebaseerd op de huidige startlijsten van ProCyclingStats.")
            st.dataframe(team[['Naam'] + list(RACES.keys())], height=700)
            
            # Samenvatting
            st.subheader("Team Bezetting")
            summary = {}
            for race in RACES.keys():
                count = (team[race] == "✅").sum()
                summary[race] = count
            
            st.bar_chart(pd.Series(summary))
