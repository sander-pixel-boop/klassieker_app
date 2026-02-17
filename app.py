import streamlit as st
import pandas as pd
import pulp
import unicodedata
import re
from difflib import get_close_matches

st.set_page_config(page_title="Klassiekers 2026", layout="wide")

# --- 1. HULPFUNCTIES VOOR MATCHING ---
def normalize_name(text):
    """Maakt namen kaal voor betere matching (geen accenten, kleine letters)."""
    if pd.isna(text): return ""
    text = str(text).lower()
    # Verwijder initialen (e.g., 't. ')
    text = re.sub(r'^[a-z]\.\s*', '', text)
    # Verwijder accenten
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.strip()

def fuzzy_merge(df_left, df_right, left_on, right_on, threshold=0.8):
    """Koppelt dataframes zelfs als namen net iets anders gespeld zijn."""
    s_left = df_left[left_on].apply(normalize_name).tolist()
    s_right = df_right[right_on].apply(normalize_name).tolist()
    
    mapping = {}
    for name in s_left:
        match = get_close_matches(name, s_right, n=1, cutoff=threshold)
        if match:
            mapping[name] = match[0]
            
    df_left['match_key'] = df_left[left_on].apply(normalize_name)
    df_right['match_key'] = df_right[right_on].apply(normalize_name)
    
    # Gebruik de mapping om de keys in df_left gelijk te maken aan die in df_right
    df_left['match_key'] = df_left['match_key'].map(mapping)
    
    return pd.merge(df_left, df_right, on='match_key', how='inner')

# --- 2. DATA INLADEN ---
@st.cache_data
def load_data():
    try:
        # Laden van bestanden (negeer delimiters door sep=None)
        df_p = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        df_wo = pd.read_csv("renners_stats.csv", sep=None, engine='python')
        df_sl = pd.read_csv("startlijsten.csv", sep=None, engine='python')

        # Kolomnamen opschonen naar HOOFDLETTERS
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        df_wo.columns = [c.strip().upper() for c in df_wo.columns]
        df_sl.columns = [c.strip().upper() for c in df_sl.columns]

        # Stap 1: Koppel Prijzen aan Stats (Fuzzy)
        df = fuzzy_merge(df_p, df_wo, 'NAAM', 'NAAM')

        # Stap 2: Koppel Startlijsten (Fuzzy)
        # We droppen de extra NAAM kolommen om chaos te voorkomen
        df_sl_clean = df_sl.copy()
        df = fuzzy_merge(df, df_sl_clean, 'NAAM_x', 'NAAM')

        # Prijs naar getal converteren
        df['PRIJS_NUM'] = pd.to_numeric(df['PRIJS'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        # Zorg dat alle koerskolommen aanwezig zijn
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        for r in races:
            if r not in df.columns:
                df[r] = 0
            df[r] = pd.to_numeric(df[r], errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"Fout bij laden van bestanden: {e}")
        return pd.DataFrame()

df = load_data()
races_all = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]

# --- 3. UI & OPTIMALISATIE ---
st.title("Klassiekers 2026")

if df.empty:
    st.info("De bestanden worden geladen of de namen konden niet gekoppeld worden. Controleer of 'Naam' in elk bestand de eerste kolom is.")
else:
    with st.sidebar:
        st.header("Strategie en Filters")
        budget = st.number_input("Budget (Euro)", value=46000000, step=500000)
        
        st.divider()
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        st.caption("OHN, KBK, E3, GW, DDV, RVV, PR")
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        st.caption("MSR, BP, AGR, WP, LBL")
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        st.caption("Parijs-Nice (PN7)")
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        st.caption("KBK, BDP, GW, SP, TA7")
        w_or  = st.slider("Eendags kwaliteit (OR)", 0, 10, 5)

        st.divider()
        # Gebruik NAAM_x omdat NAAM vaker voorkomt na de merges
        locked = st.multiselect("Vastzetten:", df['NAAM_x'].unique())
        excluded = st.multiselect("Uitsluiten:", df['NAAM_x'].unique())

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
                if row['NAAM_x'] in locked: prob += (sel[i] == 1)
                if row['NAAM_x'] in excluded: prob += (sel[i] == 0)
            
            prob.solve()
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                st.success("Team gevonden!")
            else:
                st.error("Geen oplossing mogelijk.")

        if 'team_idx' in st.session_state:
            team = df.loc[st.session_state['team_idx']]
            st.dataframe(team[['NAAM_x', 'PRIJS_NUM', 'SCORE']].sort_values('PRIJS_NUM', ascending=False), hide_index=True)
            st.metric("Totaal besteed", f"€ {team['PRIJS_NUM'].sum():,.0f}")

    with t2:
        if 'team_idx' in st.session_state:
            team_sel = df.loc[st.session_state['team_idx']].copy()
            disp = team_sel[['NAAM_x'] + races_all].copy()
            for r in races_all: disp[r] = disp[r].apply(lambda x: "✅" if x == 1 else "")
            st.dataframe(disp, hide_index=True)
            
            st.divider()
            st.subheader("Kopman Suggesties")
            kopman_list = []
            race_stats = {"OHN":"COB","KBK":"SPR","SB":"HLL","PN7":"MTN","TA7":"SPR","MSR":"SPR","BDP":"SPR","E3":"COB","GW":"COB","DDV":"COB","RVV":"COB","SP":"SPR","PR":"COB","BP":"HLL","AGR":"HLL","WP":"HLL","LBL":"HLL"}
            for r in races_all:
                starters = team_sel[team_sel[r] == 1]
                if not starters.empty:
                    top = starters.sort_values(race_stats[r], ascending=False).head(3)['NAAM_x'].tolist()
                    kopman_list.append({"Koers": r, "Top 3": " / ".join(top)})
            st.table(pd.DataFrame(kopman_list))
        else:
            st.info("Genereer eerst een team.")

    with t3:
        market = df[['NAAM_x', 'PRIJS_NUM'] + races_all].copy()
        for r in races_all: market[r] = market[r].apply(lambda x: "✅" if x == 1 else "")
        st.dataframe(market.sort_values('PRIJS_NUM', ascending=False), hide_index=True)

    with t4:
        st.write("Wiskundige optimalisatie voor Scorito 2026. Data via WielerOrakel & PCS.")
