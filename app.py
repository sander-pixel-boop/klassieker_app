import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import io

st.set_page_config(page_title="Klassiekers 2026", layout="wide")

# --- 1. CONFIGURATIE & RACES ---
YEAR = "2026"
RACES_CONFIG = {
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
races_all = list(RACES_CONFIG.keys())

# --- 2. HULPFUNCTIES ---

@st.cache_data(ttl=3600)
def scrape_pcs():
    results = {}
    for abbr, info in RACES_CONFIG.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(info["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            riders = [a.text.strip().lower() for a in soup.find_all('a', href=True) if 'rider/' in a['href']]
            results[abbr] = riders
        except:
            results[abbr] = []
    return results

@st.cache_data
def load_base_data():
    try:
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python')
        
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]

        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower().strip()
            return str(full_name).lower().strip()

        df_p['MATCH_NAME'] = df_p['NAAM'].astype(str).str.lower().str.strip()
        df_wo['MATCH_NAME'] = df_wo['NAAM'].apply(convert_to_short_name)
        
        df = pd.merge(df_p, df_wo, on='MATCH_NAME', how='inner', suffixes=('', '_WO'))
        df['PRIJS'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Fout bij laden van data: {e}")
        return pd.DataFrame()

# --- 3. UI ---
st.title("Klassiekers 2026")

df = load_base_data()

if df.empty:
    st.warning("Database leeg. Check je CSV bestanden.")
else:
    # Sidebar instellingen
    with st.sidebar:
        st.header("Strategie en Filters")
        budget = st.number_input("Budget (Euro)", value=46000000, step=500000)
        
        st.divider()
        startlist_source = st.radio("Bron Startlijsten:", ["Statisch (CSV)", "Live (PCS)"])
        
        st.divider()
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        st.caption("OHN, KBK, E3, GW, DDV, RVV, PR")
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        st.caption("MSR, BP, AGR, WP, LBL")
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        st.caption("Parijs-Nice (PN7)")
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        st.caption("KBK, BDP, GW, SP, Tirreno (TA7)")
        w_or  = st.slider("Eendags kwaliteit (OR)", 0, 10, 5)

        st.divider()
        locked_riders = st.multiselect("Renners vastzetten (Locks):", df['NAAM'].unique())
        excluded_riders = st.multiselect("Renners uitsluiten (Excludes):", df['NAAM'].unique())

    # Startlijsten koppelen op basis van keuze
    if startlist_source == "Statisch (CSV)":
        try:
            df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')
            df_sl.columns = [c.strip().upper() for c in df_sl.columns]
            df_sl['MATCH_NAME'] = df_sl['NAAM'].astype(str).str.lower().str.strip()
            df = pd.merge(df, df_sl.drop(columns=['NAAM']), on='MATCH_NAME', how='left')
        except:
            st.error("Statisch bestand niet gevonden.")
    else:
        pcs_data = scrape_pcs()
        for abbr in races_all:
            def check_pcs(match_name, race_abbr):
                last_name = match_name.split('. ')[-1]
                return 1 if any(last_name in p for p in pcs_data[race_abbr]) else 0
            df[abbr] = df['MATCH_NAME'].apply(lambda x: check_pcs(x, abbr))

    # Score berekening
    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)
    
    # CSS voor verticale headers
    st.markdown("<style>[data-testid='stDataFrame'] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); }</style>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Team Samensteller", "📅 Team Schema", "🗺️ Programma volgens PCS", "ℹ️ Informatie"])

    with tab1:
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
                st.success("Team geoptimaliseerd 🚴")
            else: st.error("Geen oplossing mogelijk.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team[['NAAM', 'PRIJS', 'SCORE', 'COB', 'HLL', 'SPR']].sort_values('PRIJS', ascending=False), hide_index=True)
            st.metric("Budget besteed", f"€ {team['PRIJS'].sum():,.0f}", f"Over: € {budget - team['PRIJS'].sum():,.0f}")

    with tab2:
        if 'team_idx' in st.session_state:
            team_schema = df.loc[st.session_state['team_idx']].copy()
            display_schema = team_schema[['NAAM'] + races_all].copy()
            for r in races_all:
                display_schema[r] = display_schema[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(display_schema, height=600, hide_index=True)
        else: st.info("Maak eerst een team.")

    with tab3:
        st.subheader("Programma volgens PCS")
        st.write("Overzicht van de gehele markt op basis van live ProCyclingStats data.")
        pcs_live = scrape_pcs()
        market_display = df[['NAAM', 'PRIJS']].copy()
        for abbr in races_all:
            def check_live(match_name, r_abbr):
                last_name = match_name.split('. ')[-1]
                return "✅" if any(last_name in p for p in pcs_live[r_abbr]) else ""
            market_display[abbr] = df['MATCH_NAME'].apply(lambda x: check_live(x, abbr))
        
        sel_race = st.selectbox("Filter op koers:", ["Alle"] + races_all)
        if sel_race != "Alle": market_display = market_display[market_display[sel_race] == "✅"]
        st.dataframe(market_display.sort_values('PRIJS', ascending=False), hide_index=True, height=700)

    with tab4:
        st.header("Informatie en Methodiek")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Over deze applicatie")
            st.write("""
            Deze tool helpt je bij het samenstellen van het optimale Scorito Klassiekerspel-team. 
            Het algoritme gebruikt een wiskundig model om de hoogste totale kwaliteit 
            binnen het budget van 46 miljoen euro te vinden.
            """)
        with col_b:
            st.subheader("Databaas & Credits")
            st.markdown("""
            * **WielerOrakel.nl:** Alle kwaliteitsratings (COB, HLL, SPR, etc.) zijn gebaseerd op hun geavanceerde modellen. 
            * **ProCyclingStats (PCS):** De live startlijsten worden rechtstreeks van PCS gescraped.
            * **Scorito.com:** Voor de officiële prijzen en de puntentelling.
            """)
        st.divider()
        st.subheader("Uitleg Ratings")
        st.markdown("""
        * **COB (Cobbles):** Kwaliteit op kasseien (RvV, Roubaix).
        * **HLL (Hills):** Kwaliteit in de heuvels (Amstel, Luik).
        * **MTN (Mountain):** Belangrijk voor de nieuwe **Parijs-Nice Etappe 7**.
        * **SPR (Sprint):** Belangrijk voor vlakke finales en **Tirreno Etappe 7**.
        * **OR (One Day Race):** Algemene score voor eendagswedstrijden.
        """)
        st.divider()
        st.write("Overzicht koerscodes:")
        r_info = {k: v['full'] for k, v in RACES_CONFIG.items()}
        c1, c2 = st.columns(2)
        for i, (k, v) in enumerate(r_info.items()):
            with (c1 if i % 2 == 0 else c2): st.write(f"**{k}**: {v}")
