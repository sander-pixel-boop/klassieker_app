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
        
        # Kolomnamen opschonen (lowercase en spaties verwijderen)
        def clean_df_columns(df):
            df.columns = [c.strip().lower() for c in df.columns]
            return df

        df_p = clean_df_columns(df_p)
        df_wo = clean_df_columns(df_wo)
        df_sl = clean_df_columns(df_sl)

        # Zorg dat de naamkolom overal 'naam' heet
        def rename_name_column(df):
            for col in df.columns:
                if col in ['naam', 'name', 'renner', 'rider']:
                    return df.rename(columns={col: 'naam'})
            return df

        df_p = rename_name_column(df_p)
        df_wo = rename_name_column(df_wo)
        df_sl = rename_name_column(df_sl)

        # Naamconversie functie (Tadej Pogačar -> t. pogačar)
        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower().strip()
            return str(full_name).lower().strip()

        # Matchkolommen maken
        df_p['match_name'] = df_p['naam'].astype(str).str.lower().str.strip()
        df_wo['match_name'] = df_wo['naam'].apply(convert_to_short_name)
        df_sl['match_name'] = df_sl['naam'].astype(str).str.lower().str.strip()
        
        # Mergen van prijzen, stats en startlijsten
        df = pd.merge(df_p, df_wo, on='match_name', how='inner', suffixes=('', '_wo'))
        df_sl_clean = df_sl.drop(columns=['naam']) if 'naam' in df_sl.columns else df_sl
        df = pd.merge(df, df_sl_clean, on='match_name', how='left')
        
        # Prijs opschonen
        price_col = 'prijs' if 'prijs' in df.columns else 'price'
        df['prijs_clean'] = pd.to_numeric(df[price_col].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        # Races voorbereiden (0/1 naar vinkjes)
        races_list = ["ohn","kbk","sb","pn7","ta7","msr","bdp","e3","gw","ddv","rvv","sp","pr","bp","agr","wp","lbl"]
        for r in races_list:
            if r in df.columns:
                df[r] = pd.to_numeric(df[r], errors='coerce').fillna(0)
            else:
                df[r] = 0
            
        # Terugzetten naar namen voor de rest van de app
        df = df.rename(columns={'naam': 'Naam', 'prijs_clean': 'Prijs_Clean'})
        # Zet race kolommen naar hoofdletters voor de weergave
        for r in races_list:
            df = df.rename(columns={r: r.upper()})
            
        return df
    except Exception as e:
        st.error(f"Fout bij laden van bestanden: {e}")
        return pd.DataFrame()

df = load_data()

# --- 2. GEDRAAIDE HEADERS CSS ---
st.markdown("""
    <style>
    [data-testid="stDataFrame"] th {
        height: 120px;
        white-space: nowrap;
    }
    [data-testid="stDataFrame"] th div {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        text-align: inherit;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. UI ---
st.title("🏆 Scorito Klassieker Master 2026")

if df.empty:
    st.info("De database is leeg. Controleer of de bestanden op GitHub staan en of de kolomnamen kloppen.")
else:
    tab1, tab2, tab3 = st.tabs(["🚀 Team Samensteller", "📅 Wedstrijdschema", "ℹ️ Informatie"])

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Instellingen")
        budget = st.number_input("Totaal Budget (€)", value=46000000, step=500000)
        
        st.divider()
        st.subheader("🎯 Strategie Gewicht")
        w_cob = st.slider("Kassei (COB)", 0, 10, 8)
        st.caption("OHN, KBK, E3, GW, DDV, RVV, PR")
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6)
        st.caption("MSR, BP, AGR, WP, LBL")
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4)
        st.caption("Parijs-Nice Etappe 7")
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5)
        st.caption("BDP, SP, TA Etappe 7")
        w_or  = st.slider("Eendags (OR)", 0, 10, 5)

    # Score berekening (stats van WO zijn hoofdletters in DF na merge)
    df['Score'] = (df['COB']*w_cob) + (df['HLL']*w_hll) + (df['MTN']*w_mtn) + (df['SPR']*w_spr) + (df['OR']*w_or)

    # --- TAB 1: SAMENSTELLER ---
    with tab1:
        col_list, col_team = st.columns([1, 1])
        with col_list:
            st.subheader("📊 Toprenners")
            st.dataframe(df[['Naam', 'Prijs_Clean', 'Score']].sort_values('Score', ascending=False).head(20))
        
        with col_team:
            st.subheader("🚀 Optimalisatie")
            if st.button("Genereer Optimaal Team"):
                prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
                sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
                prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
                prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
                prob += pulp.lpSum([sel[i] for i in df.index]) == 20
                prob.solve()
                
                if pulp.LpStatus[prob.status] == 'Optimal':
                    st.session_state['team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                    st.success("Team gevonden!")
                else:
                    st.error("Geen team mogelijk binnen budget.")

            if 'team_idx' in st.session_state:
                team = df.loc[st.session_state['team_idx']]
                st.dataframe(team[['Naam', 'Prijs_Clean', 'Score']].sort_values('Prijs_Clean', ascending=False))

    # --- TAB 2: SCHEMA ---
    with tab2:
        if 'team_idx' not in st.session_state:
            st.info("Stel eerst een team samen.")
        else:
            team_schema = df.loc[st.session_state['team_idx']].copy()
            races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
            
            # Weergave vinkjes
            for r in races:
                team_schema[r] = team_schema[r].apply(lambda x: "✅" if x == 1 else "")
            
            st.dataframe(team_schema[['Naam'] + races], height=600)
            
            summary = {r: (team_schema[r] == "✅").sum() for r in races}
            st.bar_chart(pd.Series(summary))

    # --- TAB 3: INFO ---
    with tab3:
        st.header("ℹ️ Informatie")
        st.write("Wiskundige optimalisatie voor het Scorito Klassiekerspel 2026.")
        st.markdown("""
        * **Kwaliteit:** Gebaseerd op **WielerOrakel.nl**.
        * **Startlijsten:** Gebaseerd op data van **ProCyclingStats**.
        * **Algoritme:** Vindt de 20 renners met de hoogste gecombineerde score binnen het budget.
        """)
        st.divider()
        st.write("Afkortingen:")
        st.text("OHN: Omloop, KBK: Kuurne, SB: Strade, PN7: PN Rit 7, TA7: TA Rit 7, MSR: Sanremo, BDP: De Panne, E3: E3, GW: Gent-W, DDV: Dwars door Vl, RVV: Vlaanderen, SP: Scheldeprijs, PR: Roubaix, BP: Brabantse, AGR: Amstel, WP: Waalse Pijl, LBL: Luik.")
