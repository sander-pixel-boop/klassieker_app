import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import time
import io

st.set_page_config(page_title="Scorito Master 2026", layout="wide", page_icon="🚴")

# --- 1. CONFIGURATIE & CLASSIFICATIE ---
YEAR = "2026"
RACES = {
    "Omloop Het Nieuwsblad": {"url": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist", "type": "Kassei"},
    "Kuurne-Brussel-Kuurne": {"url": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist", "type": "Sprint/Kassei"},
    "Strade Bianche": {"url": f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist", "type": "Punch"},
    "Parijs-Nice Etappe 7": {"url": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist", "type": "Klim (Nieuw!)"},
    "Tirreno-Adriatico Etappe 7": {"url": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist", "type": "Sprint (Nieuw!)"},
    "Milano-Sanremo": {"url": f"https://www.procyclingstats.com/race/milano-sanremo/{YEAR}/startlist", "type": "Sprint/Heuvel"},
    "Brugge-De Panne": {"url": f"https://www.procyclingstats.com/race/classic-brugge-de-panne/{YEAR}/startlist", "type": "Sprint"},
    "E3 Saxo Classic": {"url": f"https://www.procyclingstats.com/race/e3-harelbeke/{YEAR}/startlist", "type": "Kassei"},
    "Gent-Wevelgem": {"url": f"https://www.procyclingstats.com/race/gent-wevelgem/{YEAR}/startlist", "type": "Sprint/Kassei"},
    "Dwars door Vlaanderen": {"url": f"https://www.procyclingstats.com/race/dwars-door-vlaanderen/{YEAR}/startlist", "type": "Kassei"},
    "Ronde van Vlaanderen": {"url": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist", "type": "Kassei (Monument)"},
    "Scheldeprijs": {"url": f"https://www.procyclingstats.com/race/scheldeprijs/{YEAR}/startlist", "type": "Sprint"},
    "Parijs-Roubaix": {"url": f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist", "type": "Kassei (Monument)"},
    "Brabantse Pijl": {"url": f"https://www.procyclingstats.com/race/brabantse-pijl/{YEAR}/startlist", "type": "Heuvel/Punch"},
    "Amstel Gold Race": {"url": f"https://www.procyclingstats.com/race/amstel-gold-race/{YEAR}/startlist", "type": "Heuvel"},
    "Waalse Pijl": {"url": f"https://www.procyclingstats.com/race/fleche-wallonne/{YEAR}/startlist", "type": "Punch/Heuvel"},
    "Luik-Bastenaken-Luik": {"url": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist", "type": "Heuvel (Monument)"}
}

# --- 2. DATA INLADEN ---
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
                last_name = ' '.join(parts[1:]).replace('"', '').replace("'", "")
                return f"{parts[0][0]}. {last_name}".lower()
            return str(full_name).lower()
        df_wo['Match_Name'] = df_wo['Naam'].apply(convert_to_short_name)
        return pd.merge(df_p, df_wo, on='Match_Name', how='inner', suffixes=('', '_wo'))
    except Exception as e:
        st.error(f"Fout bij laden data: {e}")
        return pd.DataFrame()

df = load_external_data()

# --- 3. SCRAPER ---
@st.cache_data(ttl=3600)
def scrape_startlists():
    results = {}
    for race, info in RACES.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(info["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            riders = [a.text.strip().lower() for a in soup.find_all('a', href=True) if 'rider/' in a['href']]
            results[race] = list(set(riders))
        except:
            results[race] = []
    return results

# --- 4. UI STRUCTUUR ---
st.title("🏆 Scorito Klassieker Master 2026")

if df.empty:
    st.error("Data kon niet worden geladen. Check je CSV bestanden op GitHub.")
else:
    tab_solver, tab_programma, tab_info = st.tabs(["🚀 Team Samensteller", "📅 Wedstrijdschema", "ℹ️ Informatie"])

    # SIDEBAR
    with st.sidebar:
        st.header("⚙️ Instellingen")
        budget = st.number_input("Budget (€)", value=46000000, step=500000)
        st.divider()
        st.subheader("🎯 Strategie Gewicht")
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN / PN Et.7)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR / TA Et.7 / De Panne)", 0, 10, 5)
        w_or  = st.slider("Eendags kwaliteit (OR)", 0, 10, 5)
        if st.button("🔄 Ververs PCS Startlijsten"):
            st.cache_data.clear()
            st.session_state['pcs_lists'] = scrape_startlists()

    df['Score'] = (df['COB'] * w_cob) + (df['HLL'] * w_hll) + (df['MTN'] * w_mtn) + (df['SPR'] * w_spr) + (df['OR'] * w_or)

    # TAB 1
    with tab_solver:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Toprenners")
            st.dataframe(df[['Naam', 'Prijs_Clean', 'Score']].sort_values('Score', ascending=False).head(20))
        with col2:
            st.subheader("Optimalisatie")
            if st.button("Genereer Team"):
                prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
                sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
                prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
                prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
                prob += pulp.lpSum([sel[i] for i in df.index]) == 20
                prob.solve()
                if pulp.LpStatus[prob.status] == 'Optimal':
                    st.session_state['selected_team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                    st.success("Optimale balans gevonden!")
                else: st.error("Geen oplossing mogelijk binnen budget.")
            if 'selected_team_idx' in st.session_state:
                team = df.loc[st.session_state['selected_team_idx']]
                st.dataframe(team[['Naam', 'Prijs_Clean', 'Score']].sort_values('Prijs_Clean', ascending=False))

    # TAB 2
    with tab_programma:
        if 'selected_team_idx' not in st.session_state:
            st.info("Genereer eerst een team in het tabblad 'Team Samensteller'.")
        else:
            if 'pcs_lists' not in st.session_state:
                with st.spinner("Startlijsten ophalen..."):
                    st.session_state['pcs_lists'] = scrape_startlists()
            
            team = df.loc[st.session_state['selected_team_idx']].copy()
            pcs_data = st.session_state['pcs_lists']
            
            def is_on_startlist(name_short, pcs_list):
                last_name = name_short.split('. ')[-1] if '. ' in name_short else name_short
                for pcs_name in pcs_list:
                    if last_name in pcs_name: return "✅"
                return ""

            for race in RACES.keys():
                team[race] = team['Match_Name'].apply(lambda x: is_on_startlist(x, pcs_data[race]))
            
            # Kolom headers met volledige naam en type
            headers = {race: f"{race} ({info['type']})" for race, info in RACES.items()}
            st.subheader("Gedetailleerd overzicht per koers")
            st.dataframe(team[['Naam'] + list(RACES.keys())].rename(columns=headers), height=600)
            
            summary = {race: (team[race] == "✅").sum() for race in RACES.keys()}
            st.subheader("Aantal renners per koers")
            st.bar_chart(pd.Series(summary))

    # TAB 3: INFORMATIE
    with tab_info:
        st.header("Over deze applicatie")
        st.write("""
        Deze tool helpt bij het samenstellen van het optimale Scorito Klassiekerspel-team door gebruik te maken van wiskundige optimalisatie.
        """)
        
        st.subheader("Bronnen & Shout-outs")
        st.markdown("""
        De data in deze app wordt mogelijk gemaakt door:
        
        * **[WielerOrakel.nl](https://www.cyclingoracle.com/):** Een enorme shout-out voor de kwaliteitsratings (COB, HLL, SPR, etc.). Hun datamodellen vormen de kern van deze berekeningen.
        * **[ProCyclingStats (PCS)](https://www.procyclingstats.com/):** Voor de live startlijsten. Zonder hen zouden we niet weten wie er daadwerkelijk aan de start staat.
        * **[Scorito.com](https://www.scorito.com/):** Voor de prijzen en de basis van dit spel.
        """)
        
        st.subheader("Uitleg Ratings")
        st.markdown("""
        * **COB (Cobbles):** Geschiktheid voor kasseien.
        * **HLL (Hills):** Geschiktheid voor heuvels.
        * **MTN (Mountain):** Cruciaal voor de bergrit in **Parijs-Nice Etappe 7**.
        * **SPR (Sprint):** Voor de massasprints zoals **Brugge-De Panne** en **Tirreno Etappe 7**.
        * **OR (One Day Race):** Algemene indicator voor eendagswedstrijden.
        """)
