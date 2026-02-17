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
            if r in df.columns:
                df[r] = pd.to_numeric(df[r], errors='coerce').fillna(0)
            else:
                df[r] = 0
            
        return df
    except Exception as e:
        st.error(f"Fout bij laden van bestanden: {e}")
        return pd.DataFrame()

df = load_data()

# --- 2. CSS ---
st.markdown("""
    <style>
    [data-testid="stDataFrame"] th div { height: 120px; writing-mode: vertical-rl; transform: rotate(180deg); text-align: inherit; white-space: nowrap; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d3d8; }
    </style>
""", unsafe_allow_html=True)

# --- 3. UI ---
st.title("🏆 Scorito Klassieker Master 2026")

if df.empty:
    st.warning("Database leeg. Check je CSV bestanden.")
else:
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Team Samensteller", "📅 Schema", "📊 Team Analyse", "ℹ️ Info"])

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Instellingen")
        budget_total = 46000000
        budget = st.number_input("Budget (€)", value=budget_total, step=500000)
        
        st.divider()
        st.subheader("🎯 Strategie Gewicht")
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        w_or  = st.slider("Eendags (OR)", 0, 10, 5)

    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)

    # --- TAB 1: SAMENSTELLER ---
    with tab1:
        col_list, col_team = st.columns([1, 1])
        with col_list:
            st.subheader("🔍 Marktverkenning")
            st.dataframe(df[['NAAM', 'PRIJS_CLEAN', 'SCORE']].sort_values('SCORE', ascending=False).head(20))
        
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
                    st.error("Geen oplossing mogelijk.")

            if 'team_idx' in st.session_state:
                team = df.loc[st.session_state['team_idx']]
                st.dataframe(team[['NAAM', 'PRIJS_CLEAN', 'SCORE']].sort_values('PRIJS_CLEAN', ascending=False))
                
                overig = budget - team['PRIJS_CLEAN'].sum()
                st.metric("Resterend Budget", f"€ {overig:,.0f}")

    # --- TAB 2: SCHEMA ---
    with tab2:
        if 'team_idx' in st.session_state:
            team_schema = df.loc[st.session_state['team_idx']].copy()
            races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
            display_schema = team_schema[['NAAM'] + races].copy()
            for r in races:
                display_schema[r] = display_schema[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(display_schema, height=600)
        else:
            st.info("Stel eerst een team samen.")

    # --- TAB 3: TEAM ANALYSE (NIEUW) ---
    with tab3:
        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.subheader("Kracht van je team")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Gem. Kassei", f"{team['COB'].mean():.1f}")
            c2.metric("Gem. Heuvel", f"{team['HLL'].mean():.1f}")
            c3.metric("Gem. Sprint", f"{team['SPR'].mean():.1f}")
            c4.metric("Gem. Klim", f"{team['MTN'].mean():.1f}")

            st.divider()
            st.subheader("⭐ Kopman Suggesties per Koers")
            st.write("De beste 3 renners uit jouw selectie voor elke wedstrijd:")
            
            race_mapping = {
                "OHN": "COB", "KBK": "SPR", "SB": "HLL", "PN7": "MTN", "TA7": "SPR",
                "MSR": "SPR", "BDP": "SPR", "E3": "COB", "GW": "COB", "DDV": "COB",
                "RVV": "COB", "SP": "SPR", "PR": "COB", "BP": "HLL", "AGR": "HLL",
                "WP": "HLL", "LBL": "HLL"
            }
            
            kopman_data = []
            for race, stat in race_mapping.items():
                if team[race].sum() > 0: # Alleen als er mensen starten
                    starters = team[team[race] == 1]
                    top_3 = starters.sort_values(stat, ascending=False).head(3)['NAAM'].tolist()
                    kopman_data.append({"Koers": race, "Top 3 Opties": ", ".join(top_3)})
            
            st.table(pd.DataFrame(kopman_data))
        else:
            st.info("Genereer eerst een team om de analyse te bekijken.")

    # --- TAB 4: INFO ---
    with tab4:
        st.write("Wiskundige optimalisatie voor het Scorito Klassiekerspel 2026.")
