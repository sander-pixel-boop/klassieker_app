import streamlit as st
import pandas as pd
import pulp
import unicodedata
import re

st.set_page_config(page_title="Klassiekers 2026", layout="wide")

# --- 1. HULPFUNCTIE VOOR MATCHING ---
def super_clean(text):
    """Maakt namen simpel (alleen achternaam) om bestanden waterdicht te koppelen."""
    if pd.isna(text): return ""
    text = str(text).lower()
    # Verwijder accenten (bijv. ç -> c, á -> a)
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Pak de laatste naam (achternaam)
    parts = text.split()
    return parts[-1] if parts else ""

# --- 2. DATA INLADEN ---
@st.cache_data
def load_data():
    try:
        # Bestanden inladen (UTF-8-SIG negeert Excel-foutjes aan het begin van bestanden)
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python', encoding='utf-8-sig')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
        df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
        
        # Kolomnamen schoonmaken (HOOFDLETTERS en geen spaties)
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]
        df_sl.columns = [c.strip().upper() for c in df_sl.columns]
        
        # Match-keys maken
        df_p['MATCH_KEY'] = df_p['NAAM'].apply(super_clean)
        df_wo['MATCH_KEY'] = df_wo['NAAM'].apply(super_clean)
        df_sl['MATCH_KEY'] = df_sl['NAAM'].apply(super_clean)
        
        # Samenvoegen tot één grote tabel
        df = pd.merge(df_p, df_wo.drop(columns=['NAAM'], errors='ignore'), on='MATCH_KEY', how='left')
        df = pd.merge(df, df_sl.drop(columns=['NAAM'], errors='ignore'), on='MATCH_KEY', how='left')
        
        # Prijs naar getal omzetten
        df['PRIJS_NUM'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(500000)
        
        # Stats numeriek maken (als ze missen, vul aan met 20)
        for c in ['COB', 'HLL', 'MTN', 'SPR', 'OR']:
            df[c] = pd.to_numeric(df.get(c, 20), errors='coerce').fillna(20)
            
        # Koers-kolommen (1 of 0)
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
    st.warning("De database is leeg. Zorg dat renners_prijzen.csv, renners_stats.csv en startlijsten.csv op GitHub staan.")
else:
    with st.sidebar:
        st.header("Instellingen")
        budget = st.number_input("Budget", value=46000000, step=500000)
        
        st.divider()
        st.write("**Weging Scores**")
        w_cob = st.slider("Kassei", 0, 10, 8)
        w_hll = st.slider("Heuvel", 0, 10, 6)
        w_mtn = st.slider("Klim", 0, 10, 4)
        w_spr = st.slider("Sprint", 0, 10, 5)
        w_or  = st.slider("Eendag", 0, 10, 5)

        st.divider()
        locked = st.multiselect("Vastzetten in team:", df['NAAM'].unique())
        excluded = st.multiselect("Uitsluiten van team:", df['NAAM'].unique())

    # Totaalscore berekenen
    df['SCORE'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)
    
    # CSS voor schuine/verticale koerskoppen
    st.markdown("<style>[data-testid='stDataFrame'] th div { height: 100px; writing-mode: vertical-rl; transform: rotate(180deg); }</style>", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Team Samensteller", "Gekozen Programma", "Marktoverzicht"])

    with t1:
        if st.button("Genereer Optimaal Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            
            # Objective: Maximaliseer score
            prob += pulp.lpSum([df['SCORE'][i] * sel[i] for i in df.index])
            
            # Constraints
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
                st.error("Geen oplossing mogelijk binnen dit budget.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team.sort_values('PRIJS_NUM', ascending=False)[['NAAM', 'PRIJS', 'SCORE']], hide_index=True)
            st.metric("Totaal Budget Gebruikt", f"€ {team['PRIJS_NUM'].sum():,.0f}")

    with t2:
        if 'team_idx' in st.session_state:
            team_sel = df.loc[st.session_state['team_idx']].sort_values('PRIJS_NUM', ascending=False).copy()
            # Zet de enen om in vinkjes
            for r in races_all: 
                team_sel[r] = team_sel[r].apply(lambda x: "✅" if x == 1 else "")
            
            st.dataframe(team_sel[['NAAM'] + races_all], hide_index=True)
            
            st.divider()
            st.subheader("Kopman Suggesties")
            kop_data = []
            race_stats = {"OHN":"COB","KBK":"SPR","SB":"HLL","PN7":"MTN","TA7":"SPR","MSR":"SPR","BDP":"SPR","E3":"COB","GW":"COB","DDV":"COB","RVV":"COB","SP":"SPR","PR":"COB","BP":"HLL","AGR":"HLL","WP":"HLL","LBL":"HLL"}
            for r in races_all:
                starters = team_sel[team_sel[r] == "✅"]
                if not starters.empty:
                    top = starters.sort_values(race_stats[r], ascending=False).head(3)['NAAM'].tolist()
                    kop_data.append({"Koers": r, "Top 3": " / ".join(top)})
            st.table(pd.DataFrame(kop_data))
        else:
            st.info("Maak eerst een team in tab 1.")

    with t3:
        st.subheader("Volledige Lijst (Scores & Programma)")
        market = df.sort_values('PRIJS_NUM', ascending=False).copy()
        for r in races_all: 
            market[r] = market[r].apply(lambda x: "✅" if x == 1 else "")
        
        # Toon alle relevante data in één breed overzicht
        cols = ['NAAM', 'PRIJS', 'COB', 'HLL', 'SPR', 'MTN', 'OR'] + races_all
        st.dataframe(market[cols], hide_index=True)
