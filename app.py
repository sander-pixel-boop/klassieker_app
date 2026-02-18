import streamlit as st
import pandas as pd
import pulp
import unicodedata
import re

st.set_page_config(page_title="Klassiekers 2026 - Master Edition", layout="wide")

def super_clean(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    parts = text.split()
    return parts[-1] if parts else ""

@st.cache_data
def load_data():
    try:
        # Laden van bestanden
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python', encoding='utf-8-sig')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
        df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
        
        # Kolommen schoonmaken
        for d in [df_p, df_wo, df_sl]:
            d.columns = [c.strip().upper() for c in d.columns]
        
        # Match-keys maken
        df_p['MATCH_KEY'] = df_p['NAAM'].apply(super_clean)
        df_wo['MATCH_KEY'] = df_wo['NAAM'].apply(super_clean)
        df_sl['MATCH_KEY'] = df_sl['NAAM'].apply(super_clean)
        
        # STAP 1: Gebruik WielerOrakel (df_wo) als basis (Master)
        # We joinen de prijzen en startlijsten DAAROP
        df = pd.merge(df_wo, df_p[['MATCH_KEY', 'PRIJS']], on='MATCH_KEY', how='left')
        df = pd.merge(df, df_sl.drop(columns=['NAAM'], errors='ignore'), on='MATCH_KEY', how='left')
        
        # STAP 2: Opschonen
        # Prijs: als onbekend (niet in prijzen.csv), zet op 500.000
        df['PRIJS_NUM'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(500000)
        
        # Koers vinkjes: als NaN (geen match in startlijst), zet op 0
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        for r in races:
            if r in df.columns:
                df[r] = pd.to_numeric(df[r], errors='coerce').fillna(0)
            else:
                df[r] = 0
                
        # Scores numeriek maken
        for c in ['COB', 'HLL', 'MTN', 'SPR', 'OR']:
            df[c] = pd.to_numeric(df.get(c, 20), errors='coerce').fillna(20)
            
        return df
    except Exception as e:
        st.error(f"Fout bij laden: {e}")
        return pd.DataFrame()

df = load_data()
races_all = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]

st.title("Klassiekers 2026 - Alle Renners")

if df.empty:
    st.warning("Database leeg. Controleer je CSV-bestanden op GitHub.")
else:
    with st.sidebar:
        st.header("Optimalisatie")
        budget = st.number_input("Budget", value=46000000, step=500000)
        
        st.divider()
        w_cob = st.slider("Kassei", 0, 10, 8)
        w_hll = st.slider("Heuvel", 0, 10, 6)
        w_spr = st.slider("Sprint", 0, 10, 5)
        w_or  = st.slider("Eendag", 0, 10, 5)

        locked = st.multiselect("Vastzetten:", df['NAAM'].unique())
        excluded = st.multiselect("Uitsluiten:", df['NAAM'].unique())

    # Bereken totaalscore
    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['SPR']*w_spr) + (df['OR']*w_or)
    
    st.markdown("<style>[data-testid='stDataFrame'] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); }</style>", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Team Samensteller", "Gekozen Team", "Volledige Markt"])

    with t1:
        if st.button("Optimaliseer Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            prob += pulp.lpSum([df['SCORE'][i] * sel[i] for i in df.index])
            prob += pulp.lpSum([df['PRIJS_NUM'][i] * sel[i] for i in df.index]) <= budget
            prob += pulp.lpSum([sel[i] for i in df.index]) == 20
            
            for i, row in df.iterrows():
                if row['NAAM'] in locked: prob += (sel[i] == 1)
                if row['NAAM'] in excluded: prob += (sel[i] == 0)
            
            prob.solve()
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                st.success("Team samengesteld!")
            else:
                st.error("Geen oplossing gevonden.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team.sort_values('PRIJS_NUM', ascending=False)[['NAAM', 'PRIJS_NUM', 'SCORE']], hide_index=True)

    with t2:
        if 'team_idx' in st.session_state:
            team_sel = df.loc[st.session_state['team_idx']].sort_values('PRIJS_NUM', ascending=False).copy()
            for r in races_all: team_sel[r] = team_sel[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(team_sel[['NAAM'] + races_all], hide_index=True)

    with t3:
        st.subheader("WielerOrakel Database")
        st.caption("Alle renners uit de stats lijst. ✅ = Staat in startlijsten.csv")
        market = df.sort_values('PRIJS_NUM', ascending=False).copy()
        for r in races_all: market[r] = market[r].apply(lambda x: "✅" if x == 1 else "")
        st.dataframe(market[['NAAM', 'PRIJS_NUM', 'COB', 'HLL', 'SPR', 'OR'] + races_all], hide_index=True)
