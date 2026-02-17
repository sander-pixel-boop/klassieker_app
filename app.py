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

# --- 2. GEDRAAIDE HEADERS CSS ---
st.markdown("""
    <style>
    /* Pas de breedte van de kolommen aan en draai de header */
    .stDataFrame th div {
        height: 100px;
    }
    .stDataFrame th {
        vertical-align: bottom;
        text-align: center;
    }
    .rotated-header {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        white-space: nowrap;
        font-size: 14px;
        padding-bottom: 10px;
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
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(info["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            # We zoeken naar de tekst in de namen-links
            riders = [a.text.strip().lower() for a in soup.find_all('a', href=True) if 'rider/' in a['href']]
            results[abbr] = riders
        except: results[abbr] = []
    return results

df = load_external_data()

# --- 4. UI ---
st.title("🏆 Scorito Master 2026")

if df.empty:
    st.error("Data kon niet worden geladen.")
else:
    tab1, tab2, tab3 = st.tabs(["🚀 Team Samensteller", "📅 Wedstrijdschema", "ℹ️ Informatie"])

    with st.sidebar:
        st.header("⚙️ Instellingen")
        budget = st.number_input("Budget (€)", value=46000000, step=500000)
        
        st.divider()
        st.subheader("🎯 Strategie Gewicht")
        w_cob = st.slider("Kassei (COB)", 0, 10, 8, help="OHN, KBK, E3, GW, DDV, RVV, PR")
        st.caption("OHN, KBK, E3, GW, DDV, RVV, PR")
        
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6, help="MSR, BP, AGR, WP, LBL")
        st.caption("MSR, BP, AGR, WP, LBL")
        
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4, help="Parijs-Nice Etappe 7")
        st.caption("Parijs-Nice Etappe 7")
        
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5, help="KBK, MSR, BDP, GW, SP, TA Etappe 7")
        st.caption("KBK, MSR, BDP, GW, SP, TA Etappe 7")
        
        w_or  = st.slider("Eendags (OR)", 0, 10, 5, help="Algemene kwaliteit in klassiekers")
        
        st.divider()
        if st.button("🔄 Update PCS Data"):
            st.cache_data.clear()
            st.session_state['pcs_lists'] = scrape_startlists()

    # Bereken score
    df['Score'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)

    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Toprenners")
            st.dataframe(df[['Naam', 'Prijs_Clean', 'Score']].sort_values('Score', ascending=False).head(20))
        with col2:
            st.subheader("Optimalisatie")
            if st.button("Genereer Optimaal Team"):
                prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
                sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
                prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
                prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
                prob += pulp.lpSum([sel[i] for i in df.index]) == 20
                prob.solve()
                if pulp.LpStatus[prob.status] == 'Optimal':
                    st.session_state['selected_team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                    st.success("Team samengesteld!")
                else: st.error("Geen oplossing mogelijk binnen budget.")

            if 'selected_team_idx' in st.session_state:
                team_res = df.loc[st.session_state['selected_team_idx']]
                st.dataframe(team_res[['Naam', 'Prijs_Clean', 'Score']].sort_values('Prijs_Clean', ascending=False))

    with tab2:
        if 'selected_team_idx' not in st.session_state:
            st.info("Maak eerst een team bij het tabblad 'Team Samensteller'.")
        else:
            if 'pcs_lists' not in st.session_state:
                with st.spinner("Startlijsten ophalen..."):
                    st.session_state['pcs_lists'] = scrape_startlists()
            
            team = df.loc[st.session_state['selected_team_idx']].copy()
            pcs = st.session_state['pcs_lists']

            # Betere matching functie
            def check_start(name_short, race_list):
                # t. pogačar -> pogačar
                clean_name = name_short.split('. ')[-1].lower() if '. ' in name_short else name_short.lower()
                for p in race_list:
                    if clean_name in p: return "✅"
                return ""

            for abbr in RACES.keys():
                team[abbr] = team['Match_Name'].apply(lambda x: check_start(x, pcs[abbr]))

            # We gebruiken st.write met HTML voor de headers omdat de dataframe dit niet standaard kan
            st.subheader("Gedetailleerd Wedstrijdschema")
            
            # Tabel tonen
            st.dataframe(team[['Naam'] + list(RACES.keys())], height=600)
            
            # Legenda
            st.write("Aantal renners per koers:")
            counts = {abbr: (team[abbr] == "✅").sum() for abbr in RACES.keys()}
            st.bar_chart(pd.Series(counts))

    with tab3:
        st.header("ℹ️ Over deze applicatie")
        st.write("""
        Deze tool helpt bij het samenstellen van het optimale Scorito Klassiekerspel-team door gebruik te maken van wiskundige optimalisatie.
        """)
        
        st.subheader("Bronnen & Shout-outs")
        st.markdown("""
        De data in deze app wordt mogelijk gemaakt door:
        
        * **[WielerOrakel.nl](https://www.cyclingoracle.com/):** Alle kwaliteitsratings (COB, HLL, SPR, etc.) zijn gebaseerd op hun geavanceerde modellen. Een enorme shout-out naar het team van WielerOrakel voor het openbaar maken van deze data!
        * **[ProCyclingStats (PCS)](https://www.procyclingstats.com/):** Voor de live startlijsten. Zonder hen zouden we niet weten wie er daadwerkelijk aan de start staat.
        * **[Scorito.com](https://www.scorito.com/):** Voor de prijzen en de basis van dit spel.
        """)
        
        st.subheader("Uitleg Ratings")
        st.markdown("""
        * **COB (Cobbles):** Geschiktheid voor kasseien (Vlaanderen, Roubaix).
        * **HLL (Hills):** Geschiktheid voor heuvels (Amstel, Luik).
        * **MTN (Mountain):** Cruciaal voor de bergrit in **Parijs-Nice Etappe 7**.
        * **SPR (Sprint):** Voor massasprints en finales in **Tirreno Etappe 7** of Brugge-De Panne.
        * **OR (One Day Race):** Algemene indicator voor eendagswedstrijden.
        """)
        
        st.divider()
        st.write("De afkortingen in het schema staan voor:")
        cols = st.columns(2)
        r_keys = list(RACES.keys())
        for i, k in enumerate(r_keys):
            with cols[i % 2]:
                st.write(f"**{k}**: {RACES[k]['full']}")
