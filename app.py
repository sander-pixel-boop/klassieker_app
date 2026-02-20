import streamlit as st
import pandas as pd
import pulp
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Scorito Klassiekers Solver 2026", layout="wide", page_icon="🚴‍♂️")

# --- DATA LADEN & MERGEN ---
@st.cache_data
def load_and_merge_data():
    try:
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', on_bad_lines='skip')
        # Gebruikersregel: 0.8M is 750000
        df_prog.loc[df_prog['Prijs'] == 800000, 'Prijs'] = 750000
        
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        
        short_names = df_prog['Renner'].unique()
        full_names = df_stats['Renner'].unique()
        name_mapping = {}
        
        manual_overrides = {
            "Poel": "Mathieu van der Poel",
            "Aert": "Wout van Aert",
            "Lie": "Arnaud De Lie",
            "Gils": "Maxim Van Gils",
            "Berg": "Marijn van den Berg",
            "Broek": "Frank van den Broek"
        }
        
        for short in short_names:
            if short in manual_overrides:
                name_mapping[short] = manual_overrides[short]
            else:
                best_match, score = process.extractOne(short, full_names, scorer=fuzz.token_set_ratio)
                name_mapping[short] = best_match

        df_prog['Renner_Full'] = df_prog['Renner'].map(name_mapping)
        
        # Specifieke correcties voor dubbele namen
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 1500000), 'Renner_Full'] = 'Florian Vermeersch'
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Gianni Vermeersch'
        df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] == 4500000), 'Renner_Full'] = 'Mads Pedersen'

        merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='inner')
        
        if 'Renner_x' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Renner_x', 'Renner_y'])
        merged_df = merged_df.rename(columns={'Renner_Full': 'Renner'})
        merged_df = merged_df.drop_duplicates(subset=['Renner', 'Prijs'])
        
        race_cols = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'BDP', 'E3', 'GW', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
        available_races = [k for k in race_cols if k in merged_df.columns]
        
        koers_stat_map = {
            'OHN': 'COB', 'KBK': 'SPR', 'SB': 'HLL', 
            'PN': 'HLL', 'TA': 'SPR', 'MSR': 'AVG', 
            'BDP': 'SPR', 'E3': 'COB', 'GW': 'SPR', 'DDV': 'COB',
            'RVV': 'COB', 'SP': 'SPR', 'PR': 'COB', 'BP': 'HLL', 'AGR': 'HLL',
            'WP': 'HLL', 'LBL': 'HLL'
        }

        merged_df['Scorito_EV'] = 0.0
        for koers in available_races:
            stat_nodig = koers_stat_map.get(koers, 'AVG')
            merged_df[stat_nodig] = pd.to_numeric(merged_df[stat_nodig], errors='coerce').fillna(0)
            merged_df[koers] = pd.to_numeric(merged_df[koers], errors='coerce').fillna(0)
            merged_df['Scorito_EV'] += merged_df[koers] * ((merged_df[stat_nodig] / 100)**4 * 100)

        merged_df['Scorito_EV'] = merged_df['Scorito_EV'].round(0).astype(int)
        
        return merged_df, available_races, koers_stat_map

    except Exception as e:
        st.error(f"Fout: {e}")
        return pd.DataFrame(), [], {}

# --- INITIALISATIE ---
df, race_cols, koers_mapping = load_and_merge_data()

if df.empty:
    st.stop()

if "rider_multiselect" not in st.session_state:
    st.session_state.rider_multiselect = []

# --- SOLVER ---
def solve_knapsack(dataframe, total_budget, min_budget, max_riders, min_per_race, force_list, exclude_list, available_races):
    prob = pulp.LpProblem("Scorito_Solver", pulp.LpMaximize)
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe.index, cat='Binary')
    
    prob += pulp.lpSum([dataframe.loc[i, 'Scorito_EV'] * rider_vars[i] for i in dataframe.index])
    prob += pulp.lpSum([rider_vars[i] for i in dataframe.index]) == max_riders
    prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) <= total_budget
    prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) >= min_budget
    
    for koers in available_races:
        prob += pulp.lpSum([dataframe.loc[i, koers] * rider_vars[i] for i in dataframe.index]) >= min_per_race
    
    for i in dataframe.index:
        if dataframe.loc[i, 'Renner'] in force_list: prob += rider_vars[i] == 1
        if dataframe.loc[i, 'Renner'] in exclude_list: prob += rider_vars[i] == 0
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if pulp.LpStatus[prob.status] == 'Optimal':
        return [dataframe.loc[i, 'Renner'] for i in dataframe.index if rider_vars[i].varValue > 0.5]
    return None

# --- UI ---
st.title("🏆 Scorito Klassiekers 2026 AI Solver")

col_settings, col_selection = st.columns([1, 2], gap="large")

with col_settings:
    st.header("⚙️ Instellingen")
    max_renners = st.number_input("Totaal aantal renners", value=20)
    max_budget = st.number_input("Max Budget", value=45000000, step=500000)
    min_budget = st.number_input("Min Budget", value=43000000, step=500000)
    min_per_race = st.slider("Min. renners per koers", 0, 15, 8)
    
    st.divider()
    force_list = st.multiselect("🔒 Forceer renners:", options=df['Renner'].tolist())
    exclude_list = st.multiselect("❌ Sluit renners uit:", options=[r for r in df['Renner'].tolist() if r not in force_list])

    if st.button("🚀 Bereken Optimaal Team", type="primary", use_container_width=True):
        result = solve_knapsack(df, max_budget, min_budget, max_renners, min_per_race, force_list, exclude_list, race_cols)
        if result:
            st.session_state.rider_multiselect = result
            st.rerun()
        else:
            st.error("Geen oplossing mogelijk. Probeer de eisen te versoepelen.")

with col_selection:
    st.header("1. Jouw Team")
    st.multiselect("Selectie:", options=df['Renner'].tolist(), key="rider_multiselect")

# --- DASHBOARDS ---
if st.session_state.rider_multiselect:
    current_df = df[df['Renner'].isin(st.session_state.rider_multiselect)].copy()
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Budget over", f"€ {max_budget - current_df['Prijs'].sum():,.0f}")
    m2.metric("Renners", f"{len(current_df)} / {max_renners}")
    m3.metric("Team EV", f"{current_df['Scorito_EV'].sum():.0f}")

    # SECTIE 2: FINETUNER
    st.header("🔄 2. Finetuner")
    edit_df = current_df[['Renner', 'Prijs', 'Scorito_EV']].copy()
    edit_df.insert(0, 'Vervang', False)
    edited = st.data_editor(edit_df, hide_index=True, use_container_width=True, disabled=["Renner", "Prijs", "Scorito_EV"])
    
    if st.button("🔄 Vervang geselecteerde renners"):
        to_keep = edited[edited['Vervang'] == False]['Renner'].tolist()
        to_replace = edited[edited['Vervang'] == True]['Renner'].tolist()
        new_team = solve_knapsack(df, max_budget, 0, max_renners, min_per_race, 
                                  list(set(force_list + to_keep)), 
                                  list(set(exclude_list + to_replace)), 
                                  race_cols)
        if new_team:
            st.session_state.rider_multiselect = new_team
            st.rerun()

    # SECTIE 3: MATRIX
    st.header("🗓️ 3. Startlijst Matrix")
    matrix = current_df[['Renner'] + race_cols].set_index('Renner')
    matrix = matrix.applymap(lambda x: '✅' if x == 1 else '-')
    st.dataframe(matrix, use_container_width=True)

    # SECTIE 4: KOPMAN ADVIES
    st.header("🥇 4. Kopman Advies")
    kopman_lijst = []
    for koers in race_cols:
        starters = current_df[current_df[koers] == 1]
        if not starters.empty:
            stat = koers_mapping.get(koers, 'AVG')
            top = starters.sort_values(by=[stat, 'AVG'], ascending=False)['Renner'].tolist()
            kopman_lijst.append({
                "Koers": koers, "Type": stat, "Aantal": len(starters),
                "K1": top[0] if len(top)>0 else "-", 
                "K2": top[1] if len(top)>1 else "-", 
                "K3": top[2] if len(top)>2 else "-"
            })
    st.dataframe(pd.DataFrame(kopman_lijst), hide_index=True, use_container_width=True)

    # SECTIE 5: SCORES OVERZICHT
    st.header("📊 5. Team Statistieken")
    stats_overzicht = current_df[['Renner', 'COB', 'HLL', 'SPR', 'AVG', 'Total_Races', 'Prijs', 'Scorito_EV']]
    st.dataframe(stats_overzicht.sort_values(by='Scorito_EV', ascending=False), hide_index=True, use_container_width=True)
