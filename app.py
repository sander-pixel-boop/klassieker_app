import streamlit as st
import pandas as pd
import pulp
import unicodedata
import re

st.set_page_config(page_title="Klassiekers 2026", layout="wide")

# --- 1. ROBUUSTE MATCHING FUNCTIE ---
def super_clean(text):
    """Maakt namen extreem simpel: alleen de achternaam, kleine letters, geen accenten."""
    if pd.isna(text): return ""
    text = str(text).lower()
    # Verwijder voorletters en initialen
    text = re.sub(r'^[a-z]\.\s*', '', text)
    text = re.sub(r'\s[a-z]\.\s*', ' ', text)
    # Verwijder accenten
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Pak alleen de laatste naam (achternaam)
    parts = text.split()
    return parts[-1] if parts else ""

# --- 2. DATA INLADEN ---
@st.cache_data
def load_data():
    try:
        # Laden van bestanden van GitHub
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python')
        df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')

        # Kolomnamen standaardiseren naar HOOFDLETTERS
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]
        df_sl.columns = [c.strip().upper() for c in df_sl.columns]

        # Match keys maken op basis van achternaam
        df_p['MATCH_KEY'] = df_p['NAAM'].apply(super_clean)
        df_wo['MATCH_KEY'] = df_wo['NAAM'].apply(super_clean)
        df_sl['MATCH_KEY'] = df_sl['NAAM'].apply(super_clean)

        # Koppelen met 'left' join: Prijzenlijst is de leidende lijst
        df = pd.merge(df_p, df_wo.drop(columns=['NAAM'], errors='ignore'), on='MATCH_KEY', how='left')
        df = pd.merge(df, df_sl.drop(columns=['NAAM'], errors='ignore'), on='MATCH_KEY', how='left')

        # Scores invullen (NaN naar basiswaarde 20)
        score_cols = ['COB', 'HLL', 'MTN', 'SPR', 'OR']
        for c in score_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(20)
            else:
                df[c] = 20

        # Prijs numeriek maken voor berekeningen
        df['PRIJS_NUM'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(500000)
        
        # Races vullen (NaN naar 0)
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        for r in races:
            if r in df.columns:
                df[r] = pd.to_numeric(df[r], errors='coerce').fillna(0)
            else:
                df[r] = 0

        return df
    except Exception as e:
        st.error(f"Fout bij laden: {e}")
        return pd.DataFrame()

df = load_data()
races_all = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]

# --- 3. UI ---
st.title("Klassiekers 2026")

if df.empty:
    st.warning("Geen data gevonden. Controleer of de CSV-bestanden op GitHub staan.")
else:
    with st.sidebar:
        st.header("Instellingen")
        budget = st.number_input("Budget (Euro)", value=46000000, step=500000)
        
        st.divider()
        w_cob = st.slider("Kassei", 0, 10, 8)
        w_hll = st.slider("Heuvel", 0, 10, 6)
        w_mtn = st.slider("Klim (PN7)", 0, 10, 4)
        w_spr = st.slider("Sprint (TA7)", 0, 10, 5)
        w_or  = st.slider("Eendag", 0, 10, 5)

        st.divider()
        locked = st.multiselect("Vastzetten:", df['NAAM'].unique())
        excluded = st.multiselect("Uitsluiten:", df['NAAM'].unique())

    # Score berekening
    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)

    t1, t2, t3, t4 = st.tabs(["Team Samensteller", "Team Schema", "Programma", "Informatie"])

    with t1:
        if st.button("Genereer Optimaal Team"):
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
                st.success("Team gevonden!")
            else:
                st.error("Geen oplossing mogelijk binnen budget.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            # FIX: Eerst sorteren op de numerieke kolom, dan de gewenste kolommen selecteren
            team_display = team.sort_values('PRIJS_NUM', ascending=False)[['NAAM', 'PRIJS', 'SCORE']]
            st.dataframe(team_display, hide_index=True)
            st.metric("Totaal Budget Gebruikt", f"€ {team['PRIJS_NUM'].sum():,.0f}")

    with t2:
        if 'team_idx' in st.session_state:
            team_sel = df.loc[st.session_state['team_idx']].copy()
            disp = team_sel[['NAAM'] + races_all].copy()
            for r in races_all: 
                disp[r] = disp[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(disp, hide_index=True)
        else:
            st.info("Genereer eerst een team.")

    with t3:
        st.subheader("Overzicht gehele markt")
        # FIX: Eerst sorteren, dan pas kolommen filteren voor de tabel
        market_display = df.sort_values('PRIJS_NUM', ascending=False).copy()
        for r in races_all: 
            market_display[r] = market_display[r].apply(lambda x: "✅" if x == 1 else "")
        st.dataframe(market_display[['NAAM', 'PRIJS'] + races_all], hide_index=True)

    with t4:
        st.write("Wiskundige optimalisatie voor Scorito Klassiekers 2026.")
        st.write("Data bronnen: WielerOrakel & startlijsten.csv")
