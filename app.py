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

@st.cache_data(ttl=3600)
def scrape_pcs():
    results = {}
    for abbr, info in RACES_CONFIG.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
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
        df_p['MATCH_NAME'] = df_p['NAAM'].astype(str).str.lower().str.strip()
        df = pd.merge(df_p, df_wo, on='NAAM', how='inner', suffixes=('', '_WO'))
        df['PRIJS'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Fout bij laden basisdata: {e}")
        return pd.DataFrame()

# --- 3. UI ---
st.title("Klassiekers 2026")
df = load_base_data()

if not df.empty:
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

    # Startlijsten verwerken
    if startlist_source == "Statisch (CSV)":
        try:
            df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')
            df_sl.columns = [c.strip().upper() for c in df_sl.columns]
            df = pd.merge(df, df_sl.drop(columns=['NAAM']), on='NAAM', how='left').fillna(0)
        except: st.error("startlijsten.csv niet gevonden op GitHub.")
    else:
        pcs_data = scrape_pcs()
        for abbr in races_all:
            def check_pcs_match(naam_uit_db, race_abbr):
                achternaam = naam_uit_db.lower().split()[-1]
                return 1 if any(achternaam in p for p in pcs_data[race_abbr]) else 0
            df[abbr] = df['NAAM'].apply(lambda x: check_pcs_match(x, abbr))

    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)
    st.markdown("<style>[data-testid='stDataFrame'] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); }</style>", unsafe_allow_html=True)

    # Tabbladen zonder emoticons
    tab1, tab2, tab3, tab4 = st.tabs(["Team Samensteller", "Team Schema", "Programma volgens PCS", "Informatie"])

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

    with tab2:
        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']].copy()
            display_schema = team[['NAAM'] + races_all].copy()
            for r in races_all: display_schema[r] = display_schema[r].apply(lambda x: "✅" if x == 1 else "")
            st.subheader("Wedstrijdschema per renner")
            st.dataframe(display_schema, height=400, hide_index=True)
            
            st.divider()
            st.subheader("Sterkte-analyse Bezetting")
            check_data = []
            for abbr in races_all:
                aantal = int(team[abbr].sum())
                status = "✅ Voldoende"
                if aantal < 3: status = "🚨 KRITIEK: Te weinig"
                elif aantal < 5: status = "⚠️ MATIG: Weinig reserves"
                check_data.append({"Koers": abbr, "Starters": aantal, "Status": status})
            
            check_df = pd.DataFrame(check_data)
            c_warn, c_ok = st.columns(2)
            with c_warn:
                st.write("Aandachtspunten:")
                st.dataframe(check_df[check_df["Starters"] < 5], hide_index=True)
            with c_ok:
                st.write("Goed bezet:")
                st.dataframe(check_df[check_df["Starters"] >= 5], hide_index=True)

            st.divider()
            st.subheader("Kopman Suggesties")
            kopman_list = []
            for abbr, config in RACES_CONFIG.items():
                starters = team[team[abbr] == 1]
                if not starters.empty:
                    top_3 = starters.sort_values(config['stat'], ascending=False).head(3)['NAAM'].tolist()
                    kopman_list.append({"Koers": abbr, "Top 3": " / ".join(top_3)})
            st.table(pd.DataFrame(kopman_list))
        else: st.info("Maak eerst een team.")

    with tab3:
        st.subheader("Programma volgens PCS (Gehele Markt)")
        pcs_live = scrape_pcs()
        market_display = df[['NAAM', 'PRIJS']].copy()
        for abbr in races_all:
            def check_live(naam, r_abbr):
                achternaam = naam.lower().split()[-1]
                return "✅" if any(achternaam in p for p in pcs_live[r_abbr]) else ""
            market_display[abbr] = df['NAAM'].apply(lambda x: check_live(x, abbr))
        st.dataframe(market_display.sort_values('PRIJS', ascending=False), hide_index=True, height=600)

    with tab4:
        st.header("Informatie en Methodiek")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Over deze applicatie")
            st.write("Optimaliseer je Scorito team middels wiskundige modellen.")
        with c2:
            st.subheader("Databaas & Credits")
            st.markdown("* WielerOrakel.nl: Ratings\n* ProCyclingStats: Startlijsten\n* Scorito.com: Prijzen")
        st.divider()
        st.subheader("Uitleg Ratings")
        st.write("COB: Kassei, HLL: Heuvel, MTN: Klim (PN), SPR: Sprint (BDP/TA), OR: Eendagskwaliteit")
        st.divider()
        c3, c4 = st.columns(2)
        for i, (k, v) in enumerate({k: v['full'] for k, v in RACES_CONFIG.items()}.items()):
            with (c3 if i % 2 == 0 else c4): st.write(f"**{k}**: {v}")
