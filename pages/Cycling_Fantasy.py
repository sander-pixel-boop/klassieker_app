import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
from thefuzz import process, fuzz
import io

# --- CONFIGURATIE ---
st.set_page_config(page_title="Cycling Fantasy AI", layout="wide", page_icon="🚲")

# --- STATISCHE DATA LADEN (STATS + PRIJZEN) ---
@st.cache_data
def load_static_data():
    try:
        # 1. Stats laden
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        if 'Team' not in df_stats.columns and 'Ploeg' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Ploeg': 'Team'})
        df_stats = df_stats.drop_duplicates(subset=['Renner'], keep='first')

        all_stats_cols = ['COB', 'HLL', 'SPR', 'AVG', 'FLT', 'MTN', 'ITT', 'GC', 'OR', 'TTL']
        for col in all_stats_cols:
            if col not in df_stats.columns:
                df_stats[col] = 0
            df_stats[col] = pd.to_numeric(df_stats[col], errors='coerce').fillna(0).astype(int)

        if 'Team' not in df_stats.columns:
            df_stats['Team'] = 'Onbekend'
        else:
            df_stats['Team'] = df_stats['Team'].fillna('Onbekend')

        # 2. Prijzen laden (CF Credits)
        try:
            df_prices = pd.read_csv("cf_prijzen.csv", sep=None, engine='python')
            if 'Naam' in df_prices.columns:
                df_prices = df_prices.rename(columns={'Naam': 'Renner'})
        except FileNotFoundError:
            st.warning("⚠️ Bestand 'cf_prijzen.csv' niet gevonden. Alle renners krijgen de standaardprijs (200).")
            df_prices = pd.DataFrame(columns=['Renner', 'Prijs'])

        # Koppel prijzen aan de stats via Fuzzy Match
        full_names = df_stats['Renner'].tolist()
        def match_name(name):
            match = process.extractOne(name, full_names, scorer=fuzz.token_set_ratio)
            return match[0] if match and match[1] > 80 else name

        if not df_prices.empty:
            df_prices['Renner_Matched'] = df_prices['Renner'].apply(match_name)
            df_stats = pd.merge(df_stats, df_prices[['Renner_Matched', 'Prijs']], left_on='Renner', right_on='Renner_Matched', how='left')
            df_stats = df_stats.drop(columns=['Renner_Matched'])
        else:
            df_stats['Prijs'] = 200

        # CF Regel: Niet in de lijst = 200 credits
        df_stats['Prijs'] = df_stats['Prijs'].fillna(200).astype(int)

        return df_stats
    except Exception as e:
        st.error(f"Fout bij laden statische data: {e}")
        return pd.DataFrame()

# --- STARTLIJST VERWERKEN ---
def process_startlist(uploaded_file, df_static):
    try:
        if uploaded_file.name.endswith('.csv'):
            df_start = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df_start = pd.read_excel(uploaded_file)
            
        # Zoek de kolom met namen
        col_name = None
        for col in ['Renner', 'Rider', 'Naam', 'Name']:
            if col in df_start.columns:
                col_name = col
                break
        if not col_name:
            col_name = df_start.columns[0] # Pak de eerste kolom als fallback
            
        df_start = df_start.rename(columns={col_name: 'Renner'})
        
        # Fuzzy match de geüploade namen aan de statische database
        full_names = df_static['Renner'].tolist()
        def match_name_upload(name):
            match = process.extractOne(str(name), full_names, scorer=fuzz.token_set_ratio)
            return match[0] if match and match[1] > 75 else str(name)
            
        df_start['Renner_Matched'] = df_start['Renner'].apply(match_name_upload)
        
        # Merge de startlijst met de database
        df_race = pd.merge(df_start[['Renner_Matched']], df_static, left_on='Renner_Matched', right_on='Renner', how='inner')
        return df_race.drop_duplicates(subset=['Renner'])
    except Exception as e:
        st.error(f"Fout bij verwerken startlijst: {e}")
        return pd.DataFrame()

# --- CF EV CALCULATOR ---
def calculate_cf_ev(df, stat, method):
    df = df.copy()
    df = df.sort_values(by=[stat, 'AVG'], ascending=[False, False]).reset_index(drop=True)
    
    # CF Punten ranking simulatie
    cf_pts = [45, 25, 22, 19, 17, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    
    df['CF_EV'] = 0.0
    for i, idx in enumerate(df.index):
        val = 0.0
        if "Ranking (CF Punten)" in method:
            val = cf_pts[i] if i < len(cf_pts) else 0.0
        elif "Macht 4 Curve" in method:
            val = (df.loc[idx, stat] / 100)**4 * 45
            
        df.at[idx, 'CF_EV'] = val
        
    df['Waarde (EV/Credit)'] = (df['CF_EV'] / df['Prijs']).replace([float('inf'), -float('inf')], 0).fillna(0).round(4)
    return df

def bepaal_klassieker_type(row):
    cob = row.get('COB', 0)
    hll = row.get('HLL', 0)
    spr = row.get('SPR', 0)
    elite = []
    if cob >= 85: elite.append('Kassei')
    if hll >= 85: elite.append('Heuvel')
    if spr >= 85: elite.append('Sprint')
    if len(elite) == 3: return 'Allround / Multispecialist'
    elif len(elite) == 2: return ' / '.join(elite)
    elif len(elite) == 1: return elite[0]
    else:
        s = {'Kassei': cob, 'Heuvel': hll, 'Sprint': spr, 'Klimmer': row.get('MTN', 0), 'Tijdrit': row.get('ITT', 0), 'Klassement': row.get('GC', 0)}
        if sum(s.values()) == 0: return 'Onbekend'
        return max(s, key=s.get)

# --- SOLVER CYCLING FANTASY ---
def solve_cf_team(dataframe, total_budget, force_list, exclude_list):
    prob = pulp.LpProblem("CF_Solver", pulp.LpMaximize)
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe.index, cat='Binary')
    
    prob += pulp.lpSum([dataframe.loc[i, 'CF_EV'] * rider_vars[i] for i in dataframe.index])
    prob += pulp.lpSum([rider_vars[i] for i in dataframe.index]) == 9
    prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) <= total_budget
    
    for i in dataframe.index:
        renner = dataframe.loc[i, 'Renner']
        if renner in force_list: prob += rider_vars[i] == 1
        if renner in exclude_list: prob += rider_vars[i] == 0
            
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))
    if pulp.LpStatus[prob.status] == 'Optimal':
        return [dataframe.loc[i, 'Renner'] for i in dataframe.index if rider_vars[i].varValue > 0.5]
    return None

# --- HOOFDCODE ---
df_static = load_static_data()

if df_static.empty:
    st.warning("Database kon niet geladen worden.")
    st.stop()

# --- SIDEBAR (CONTROLECENTRUM) ---
with st.sidebar:
    st.title("🚲 CF AI Coach")
    
    st.header("📂 1. Upload Startlijst")
    uploaded_file = st.file_uploader("Upload CSV/Excel (met kolom 'Renner')", type=['csv', 'xlsx'])
    
    st.header("⚙️ 2. Instellingen")
    stat_mapping = {
        'Kasseien (COB)': 'COB',
        'Heuvels/Ardennen (HLL)': 'HLL',
        'Vlakke Sprint (SPR)': 'SPR',
        'Allround / Monument (AVG)': 'AVG',
        'Klimmen (MTN)': 'MTN',
        'Tijdrit (ITT)': 'ITT'
    }
    koers_type = st.selectbox("🏁 Type Koers:", list(stat_mapping.keys()))
    selected_stat = stat_mapping[koers_type]
    
    ev_method = st.selectbox("🧮 Rekenmodel (EV)", ["1. Ranking (CF Punten)", "2. Macht 4 Curve"])
    max_bud = st.number_input("💰 Budget (Credits)", value=5000, step=200)
    
    df_race = pd.DataFrame()
    if uploaded_file is not None:
        raw_race = process_startlist(uploaded_file, df_static)
        if not raw_race.empty:
            df_race = calculate_cf_ev(raw_race, selected_stat, ev_method)
            df_race['Type'] = df_race.apply(bepaal_klassieker_type, axis=1)
            
            st.divider()
            with st.expander("🔒 Renners Forceren / Uitsluiten", expanded=False):
                force_list = st.multiselect("🟢 Moet in team:", options=df_race['Renner'].tolist())
                exclude_list = st.multiselect("🚫 Compleet negeren:", options=[r for r in df_race['Renner'].tolist() if r not in force_list])

            st.write("")
            if st.button("🚀 BEREKEN CF TEAM", type="primary", use_container_width=True):
                res = solve_cf_team(df_race, max_bud, force_list, exclude_list)
                if res:
                    st.session_state.cf_team = res
                else:
                    st.error("Geen oplossing mogelijk. Check je budget of geforceerde renners.")

st.title("🚲 Cycling Fantasy: Race Optimizer")

if uploaded_file is None:
    st.info("👈 Begin met het uploaden van een startlijst in de zijbalk.")
    
    # Format voorbeeld tonen
    st.markdown("**Hoe moet je startlijst eruit zien?**")
    st.markdown("Maak een simpel Excel of CSV bestand met tenminste de kolomnaam `Renner`. Kopieer namen direct van ProCyclingStats.")
    st.code("Renner\nTadej Pogacar\nMathieu van der Poel\nWout van Aert")

elif not df_race.empty:
    if "cf_team" in st.session_state and st.session_state.cf_team:
        team_df = df_race[df_race['Renner'].isin(st.session_state.cf_team)].copy()
        
        # SORTEER OP EV VOOR DE CF TIE-BREAKER MULTIPLIER!
        team_df = team_df.sort_values(by='CF_EV', ascending=False).reset_index(drop=True)
        
        multipliers = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
        team_df['Tie-Breaker (Volgorde)'] = [f"#{i+1} (x{m})" for i, m in enumerate(multipliers)]
        
        st.subheader(f"🏆 Optimaal Team (Focus: {selected_stat})")
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Budget Gebruikt", f"{team_df['Prijs'].sum():.0f} / {max_bud}")
        m2.metric("🚴 Renners", "9 / 9")
        m3.metric("🎯 Verwachte Punten (EV)", f"{team_df['CF_EV'].sum():.1f}")
        
        st.info("💡 **Tie-Breaker Tip:** Zet je renners exact in deze volgorde in de CF App. De sterkste renners staan bovenaan voor de hoogste multiplier bij een gelijkspel.")
        
        display_team = team_df[['Tie-Breaker (Volgorde)', 'Renner', 'Team', 'Type', 'Prijs', 'CF_EV', selected_stat]]
        st.dataframe(display_team, hide_index=True, use_container_width=True)
        
        st.header("📈 Team Analyse")
        c1, c2 = st.columns(2)
        with c1:
            fig_donut = px.pie(team_df, values='Prijs', names='Type', hole=0.4, title="Budget Verdeling per Type")
            st.plotly_chart(fig_donut, use_container_width=True)
        with c2:
            fig_teams = px.bar(team_df['Team'].value_counts().reset_index().rename(columns={'count':'Aantal'}), x='Team', y='Aantal', title="Spreiding per Ploeg", text_auto=True)
            st.plotly_chart(fig_teams, use_container_width=True)
    else:
        st.info("👈 Klik op **Bereken CF Team** in de zijbalk.")

    st.divider()
    st.header(f"📋 Ingeladen Startlijst Database")
    db_display = df_race[['Renner', 'Team', 'Prijs', 'CF_EV', 'Waarde (EV/Credit)', 'Type', selected_stat]].sort_values(by='CF_EV', ascending=False)
    st.dataframe(db_display, hide_index=True, use_container_width=True)
