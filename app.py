import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import io

st.set_page_config(page_title="Scorito Master 2026", layout="wide", page_icon="🚴")

# --- 1. CONFIGURATIE & AFKORTINGEN ---
YEAR = "2026"
RACES = {
    "OHN": {"url": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist", "full": "Omloop Het Nieuwsblad"},
    "KBK": {"url": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist", "full": "Kuurne-Brussel-Kuurne"},
    "SB":  {"url": f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist", "full": "Strade Bianche"},
    "PN7": {"url": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist", "full": "Parijs-Nice Etappe 7"},
    "TA7": {"url": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist", "full": "Tirreno-Adriatico Etappe 7"},
    "MSR": {"url": f"https://www.procyclingstats.com/race/milano-sanremo/{YEAR}/startlist", "full": "Milano-Sanremo"},
    "BDP": {"url": f"https://www.procyclingstats.com/race/classic-brugge-de-panne/{YEAR}/startlist", "full": "Brugge-De Panne"},
    "E3":  {"url": f"https://www.procyclingstats.com/race/e3-harelbeke/{YEAR}/startlist", "full": "E3 Saxo Classic"},
    "GW":  {"url": f"https://www.procyclingstats.com/race/gent-wevelgem/{YEAR}/startlist", "full": "Gent-Wevelgem"},
    "DDV": {"url": f"https://www.procyclingstats.com/race/dwars-door-vlaanderen/{YEAR}/startlist", "full": "Dwars door Vlaanderen"},
    "RVV": {"url": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist", "full": "Ronde van Vlaanderen"},
    "SP":  {"url": f"https://www.procyclingstats.com/race/scheldeprijs/{YEAR}/startlist", "full": "Scheldeprijs"},
    "PR":  {"url": f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist", "full": "Parijs-Roubaix"},
    "BP":  {"url": f"https://www.procyclingstats.com/race/brabantse-pijl/{YEAR}/startlist", "full": "Brabantse Pijl"},
    "AGR": {"url": f"https://www.procyclingstats.com/race/amstel-gold-race/{YEAR}/startlist", "full": "Amstel Gold Race"},
    "WP":  {"url": f"https://www.procyclingstats.com/race/fleche-wallonne/{YEAR}/startlist", "full": "Waalse Pijl"},
    "LBL": {"url": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist", "full": "Luik-Bastenaken-Luik"}
}

# --- 2. CUSTOM CSS VOOR GEDRAAIDE HEADERS ---
st.markdown("""
    <style>
    th.header {
        height: 120px;
        white-space: nowrap;
    }
    th.header div {
        transform: translate(10px, 40px) rotate(-90deg);
        width: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATA & SCRAPER ---
@st.cache_data
def load_external_data():
    try:
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python', on_bad_lines='skip')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python', on_bad_lines='skip')
        df_p.columns = df_p.columns.str.strip()
        df_wo.columns = df_wo.columns.str.strip()
        df_p['Prijs_Clean'] = pd.to_numeric(df_p['Prijs'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        df_p['Match_Name'] = df_p['Naam'].str.lower().str.strip()
        
        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower()
            return str(full_name).lower()
            
        df_wo['Match_Name'] = df_wo['Naam'].apply(convert_to_short_name)
        return pd.merge(df_p, df_wo, on='Match_Name', how='inner', suffixes=('', '_wo'))
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def scrape_startlists():
    results = {}
    for abbr, info in RACES.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(info["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            # Pak alle namen uit de links en vervang streepjes door spaties voor betere match
            riders = [a['href'].split('/')[-1].replace('-', ' ').lower() for a in soup.find_all('a', href=True) if 'rider/' in a['href']]
            results[abbr] = riders
        except: results[abbr] = []
    return results

df = load_external_data()

# --- 4. UI ---
st.title("🏆 Scorito Master 2026")

if df.empty:
    st.error("Data kon niet worden geladen.")
else:
    tab1, tab2, tab3 = st.tabs(["🚀 Team", "📅 Schema", "ℹ️ Info"])

    with st.sidebar:
        budget = st.number_input("Budget (€)", value=46000000, step=500000)
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        w_or  = st.slider("Eendags (OR)", 0, 10, 5)
        if st.button("🔄 Update PCS Data"):
            st.cache_data.clear()
            st.session_state['pcs_lists'] = scrape_startlists()

    df['Score'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)

    with tab1:
        if st.button("Genereer Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
            prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
            prob += pulp.lpSum([sel[i] for i in df.index]) == 20
            prob.solve()
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['selected_team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                st.success("Team samengesteld!")
            else: st.error("Geen team mogelijk binnen budget.")

        if 'selected_team_idx' in st.session_state:
            st.dataframe(df.loc[st.session_state['selected_team_idx'], ['Naam', 'Prijs_Clean', 'Score']].sort_values('Prijs_Clean', ascending=False))

    with tab2:
        if 'selected_team_idx' not in st.session_state:
            st.info("Maak eerst een team bij het tabblad 'Team'.")
        else:
            if 'pcs_lists' not in st.session_state:
                st.session_state['pcs_lists'] = scrape_startlists()
            
            team = df.loc[st.session_state['selected_team_idx']].copy()
            pcs = st.session_state['pcs_lists']

            # Robuuste match functie
            def check_start(name_short, race_list):
                # Pak achternaam: "t. pogačar" -> "pogačar"
                last_name = name_short.split('. ')[-1].lower() if '. ' in name_short else name_short.lower()
                # Check of achternaam in een van de namen op de PCS lijst staat
                return "✅" if any(last_name in p for p in race_list) else ""

            for abbr in RACES.keys():
                team[abbr] = team['Match_Name'].apply(lambda x: check_start(x, pcs[abbr]))

            # Display tabel met afkortingen
            st.subheader("Wedstrijdschema (✅ = op PCS startlijst)")
            st.dataframe(team[['Naam'] + list(RACES.keys())], height=600)

    with tab3:
        st.header("Bronnen")
        st.write("Data: **WielerOrakel.nl** & **ProCyclingStats**.")
        st.write("De afkortingen in de tabel staan voor:")
        for k, v in RACES.items():
            st.write(f"**{k}**: {v['full']}")
