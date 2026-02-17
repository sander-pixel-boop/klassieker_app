import streamlit as st
import pandas as pd
import pulp
import io

st.set_page_config(page_title="Scorito Master 2026", layout="wide", page_icon="🚴")

# --- 1. DATA INLADEN & ROBUUSTE MATCHING ---
@st.cache_data
def load_data():
    try:
        # Laden van de drie bestanden
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python')
        df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')
        
        # Kolomnamen direct opschonen naar UPPERCASE om KeyErrors te voorkomen
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]
        df_sl.columns = [c.strip().upper() for c in df_sl.columns]

        # Naamconversie functie (Tadej Pogačar -> t. pogačar)
        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower().strip()
            return str(full_name).lower().strip()

        # Matchkolommen maken (altijd kleine letters voor de match)
        df_p['MATCH_NAME'] = df_p['NAAM'].astype(str).str.lower().str.strip()
        df_wo['MATCH_NAME'] = df_wo['NAAM'].apply(convert_to_short_name)
        df_sl['MATCH_NAME'] = df_sl['NAAM'].astype(str).str.lower().str.strip()
        
        # Stap 1: Prijzen + Stats
        df = pd.merge(df_p, df_wo, on='MATCH_NAME', how='inner', suffixes=('', '_WO'))
        
        # Stap 2: Startlijsten toevoegen
        cols_to_drop = [c for c in df_sl.columns if c in df.columns and c != 'MATCH_NAME']
        df_sl_clean = df_sl.drop(columns=cols_to_drop)
        df = pd.merge(df, df_sl_clean, on='MATCH_NAME', how='left')
        
        # Prijs opschonen
        df['PRIJS_CLEAN'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        # Zorg dat race kolommen (OHN, KBK etc) aanwezig zijn en gevuld met 0/1
        races_list = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        for r in races_list:
            if r in df.columns:
                df[r] = pd.to_numeric(df[r], errors='coerce').fillna(0)
            else:
                df[r] = 0
            
        return df
    except Exception as e:
        st.error(f"Fout bij laden van bestanden: {e}")
        return pd.DataFrame()

df = load_data()

# --- 2. GEDRAAIDE HEADERS CSS ---
st.markdown("""
    <style>
    [data-testid="stDataFrame"] th div {
        height: 120px;
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        text-align: inherit;
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. UI ---
st.title("🏆 Scorito Klassieker Master 2026")

if df.empty:
    st.warning("De database is leeg. Controleer of de namen in 'renners_prijzen.csv' en 'renners_stats.csv' wel matchen.")
else:
    tab1, tab2, tab3 = st.tabs(["🚀 Team Samensteller", "📅 Wedstrijdschema", "ℹ️ Informatie"])

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Instellingen")
        budget = st.number_input("Totaal Budget (€)", value=46000000, step=500000)
        
        st.divider()
        st.subheader("🎯 Strategie Gewicht")
        # We gebruiken hier de exacte hoofdletters uit de CSV
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        w_or  = st.slider("Eendags (OR)", 0, 10, 5)

    # Berekening met foutafhandeling voor kolomnamen
    try:
        df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)
    except KeyError as e:
        st.error(f"Kolom niet gevonden in renners_stats.csv: {e}")
        st.stop()

    # --- TAB 1: SAMENSTELLER ---
    with tab1:
        col_list, col_team = st.columns([1, 1])
        with col_list:
            st.subheader("📊 Toprenners")
            st.dataframe(df[['NAAM', 'PRIJS_CLEAN', 'SCORE']].sort_values('SCORE', ascending=False).head(25))
        
        with col_team:
            st.subheader("🚀 Optimalisatie")
            if st.button("Genereer Optimaal Team"):
                prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
                sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
                prob += pulp.lpSum([df['SCORE'][i] * sel[i] for i in df.index])
                prob += pulp.lpSum([df['PRIJS_CLEAN'][i] * sel[i] for i in df.index]) <= budget
                prob += pulp.lpSum([sel[i] for i in df.index]) == 20
                prob.solve()
                
                if pulp.LpStatus[prob.status] == 'Optimal':
                    st.session_state['team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                    st.success("Team gevonden!")
                else:
                    st.error("Geen team mogelijk binnen budget.")

            if 'team_idx' in st.session_state:
                team = df.loc[st.session_state['team_idx']]
                st.dataframe(team[['NAAM', 'PRIJS_CLEAN', 'SCORE']].sort_values('PRIJS_CLEAN', ascending=False))

    # --- TAB 2: SCHEMA ---
    with tab2:
        if 'team_idx' not in st.session_state:
            st.info("Stel eerst een team samen.")
        else:
            team_schema = df.loc[st.session_state['team_idx']].copy()
            races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
            
            # Weergave vinkjes
            display_schema = team_schema[['NAAM'] + races].copy()
            for r in races:
                display_schema[r] = display_schema[r].apply(lambda x: "✅" if x == 1 else "")
            
            st.dataframe(display_schema, height=600)

    # --- TAB 3: INFO ---
    with tab3:
        st.header("ℹ️ Informatie")
        st.write("Data: WielerOrakel.nl & ProCyclingStats.")
