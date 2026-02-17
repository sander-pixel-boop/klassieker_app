import streamlit as st
import pandas as pd
import pulp
import io

st.set_page_config(page_title="Scorito Master 2026", layout="wide", page_icon="🚴")

# --- 1. DATA INLADEN ---
@st.cache_data
def load_data():
    try:
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python')
        df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')
        
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]
        df_sl.columns = [c.strip().upper() for c in df_sl.columns]

        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower().strip()
            return str(full_name).lower().strip()

        df_p['MATCH_NAME'] = df_p['NAAM'].astype(str).str.lower().str.strip()
        df_wo['MATCH_NAME'] = df_wo['NAAM'].apply(convert_to_short_name)
        df_sl['MATCH_NAME'] = df_sl['NAAM'].astype(str).str.lower().str.strip()
        
        df = pd.merge(df_p, df_wo, on='MATCH_NAME', how='inner', suffixes=('', '_WO'))
        
        cols_to_drop = [c for c in df_sl.columns if c in df.columns and c != 'MATCH_NAME']
        df_sl_clean = df_sl.drop(columns=cols_to_drop)
        df = pd.merge(df, df_sl_clean, on='MATCH_NAME', how='left')
        
        df['PRIJS_CLEAN'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        races_list = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        for r in races_list:
            df[r] = pd.to_numeric(df.get(r, 0), errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Fout bij laden van bestanden: {e}")
        return pd.DataFrame()

df = load_data()
races_all = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]

# --- 2. CSS ---
st.markdown("""
    <style>
    [data-testid="stDataFrame"] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); text-align: inherit; white-space: nowrap; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 3. UI ---
st.title("🏆 Scorito Klassieker Master 2026")

if df.empty:
    st.warning("Database leeg. Check je CSV bestanden.")
else:
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Team Samensteller", "📅 Team Schema", "🗺️ PCS Markt-Programma", "ℹ️ Informatie"])

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Strategie & Filters")
        budget = st.number_input("Budget (€)", value=46000000, step=500000)
        
        st.divider()
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        w_or  = st.slider("Eendags (OR)", 0, 10, 5)

        st.divider()
        st.subheader("📌 Renners Vastzetten (Locks)")
        locked_riders = st.multiselect("Deze renners MOETEN in het team:", df['NAAM'].unique())
        
        st.subheader("🚫 Renners Uitsluiten (Excludes)")
        excluded_riders = st.multiselect("Deze renners NOOIT meenemen:", df['NAAM'].unique())

    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)

    # --- TAB 1: SAMENSTELLER ---
    with tab1:
        if st.button("🔄 Genereer Optimaal Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            
            prob += pulp.lpSum([df['SCORE'][i] * sel[i] for i in df.index])
            prob += pulp.lpSum([df['PRIJS_CLEAN'][i] * sel[i] for i in df.index]) <= budget
            prob += pulp.lpSum([sel[i] for i in df.index]) == 20
            
            # Constraints voor Locks & Excludes
            for i, row in df.iterrows():
                if row['NAAM'] in locked_riders:
                    prob += (sel[i] == 1)
                if row['NAAM'] in excluded_riders:
                    prob += (sel[i] == 0)
            
            prob.solve()
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                st.success("Team geoptimaliseerd met jouw voorkeuren!")
            else:
                st.error("Geen oplossing mogelijk. Check je budget of het aantal 'Locks'.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team[['NAAM', 'PRIJS_CLEAN', 'SCORE', 'COB', 'HLL', 'SPR']].sort_values('PRIJS_CLEAN', ascending=False))
            st.metric("Totaal besteed", f"€ {team['PRIJS_CLEAN'].sum():,.0f}", f"Over: € {budget - team['PRIJS_CLEAN'].sum():,.0f}")

    # --- TAB 2: TEAM SCHEMA ---
    with tab2:
        if 'team_idx' in st.session_state:
            team_schema = df.loc[st.session_state['team_idx']].copy()
            display_schema = team_schema[['NAAM'] + races_all].copy()
            for r in races_all:
                display_schema[r] = display_schema[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(display_schema, height=600)
        else:
            st.info("Genereer eerst een team.")

    # --- TAB 3: PCS MARKT-PROGRAMMA (NIEUW) ---
    with tab3:
        st.subheader("Wie rijdt wat? (Gehele Markt)")
        st.write("Dit overzicht toont alle beschikbare renners en hun startlijst-status bij PCS.")
        
        race_filter = st.selectbox("Filter op wedstrijd:", ["Alle Wedstrijden"] + races_all)
        
        market_display = df[['NAAM', 'PRIJS_CLEAN'] + races_all].copy()
        for r in races_all:
            market_display[r] = market_display[r].apply(lambda x: "✅" if x == 1 else "")
        
        if race_filter != "Alle Wedstrijden":
            market_display = market_display[market_display[race_filter] == "✅"]
            
        st.dataframe(market_display.sort_values('PRIJS_CLEAN', ascending=False), height=700)

    # --- TAB 4: INFORMATIE ---
    with tab4:
        st.header("ℹ️ Informatie & Methodiek")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Hoe werkt de optimalisatie?")
            st.write("""
            Deze tool maakt gebruik van *Linear Programming*. In plaats van zelf te puzzelen, 
            berekent de computer de mathematisch beste combinatie van 20 renners. 
            Het model kijkt naar de totale 'Score' die jij aan de renners geeft via de sliders 
            en zorgt dat het team nooit boven het ingestelde budget komt.
            """)
        
        with col_b:
            st.subheader("De Kracht van WielerOrakel")
            st.write("""
            Ratings zoals **COB** (Cobbles) en **HLL** (Hills) zijn gebaseerd op de 
            machine-learning modellen van **WielerOrakel.nl**. Deze cijfers (0-100) 
            geven een veel nauwkeuriger beeld van de kansen van een renner dan de 
            standaard sterren van Scorito.
            """)

        st.divider()
        st.subheader("Nieuwe Koersen in 2026")
        st.info("**Parijs-Nice (Et. 7)** en **Tirreno-Adriatico (Et. 7)** zijn dit jaar toegevoegd. De app weegt hiervoor de 'Klim' (MTN) en 'Sprint' (SPR) ratings mee, aangezien dit respectievelijk een bergrit en een massasprint zijn.")

        st.subheader("Credits")
        st.markdown("""
        - **Ratings:** [WielerOrakel.nl](https://www.cyclingoracle.com/)
        - **Startlijsten:** [ProCyclingStats.com](https://www.procyclingstats.com/)
        - **Prijzen:** [Scorito.com](https://www.scorito.com/)
        """)
