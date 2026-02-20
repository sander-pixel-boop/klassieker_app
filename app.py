import streamlit as st
import pandas as pd
import pulp
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Scorito Klassiekers Solver 2026", layout="wide", page_icon="🚴‍♂️")

# --- DATA LADEN & MERGEN ---
@st.cache_data
def load_and_merge_data():
    # Verbeterde CSV import: sep=None detecteert zelf komma of puntkomma
    # on_bad_lines='skip' voorkomt dat de app crasht bij een typefout in de CSV
    try:
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', on_bad_lines='skip')
    except Exception as e:
        st.error(f"Fout bij lezen bron_startlijsten.csv: {e}")
        st.stop()

    # Stats inladen (tab-gescheiden)
    try:
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
    except Exception as e:
        st.error(f"Fout bij lezen renners_stats.csv: {e}")
        st.stop()
    
    if 'Naam' in df_stats.columns:
        df_stats = df_stats.rename(columns={'Naam': 'Renner'})
    
    short_names = df_prog['Renner'].unique()
    full_names = df_stats['Renner'].unique()
    name_mapping = {}
    
    # Handmatige overrides
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
    
    # Correcties voor dubbele namen en prijzen (0.8M = 750k)
    df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 1500000), 'Renner_Full'] = 'Florian Vermeersch'
    df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] <= 800000), 'Renner_Full'] = 'Gianni Vermeersch'
    df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] >= 4000000), 'Renner_Full'] = 'Mads Pedersen'
    df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] <= 800000), 'Renner_Full'] = 'Rasmus Søjberg Pedersen'

    merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='inner')
    
    if 'Renner_x' in merged_df.columns:
        merged_df = merged_df.drop(columns=['Renner_x', 'Renner_y'])
    merged_df = merged_df.rename(columns={'Renner_Full': 'Renner'})
    
    merged_df = merged_df.drop_duplicates(subset=['Renner', 'Prijs'])
    merged_df['Display'] = merged_df['Renner'] + " - " + (merged_df['Prijs'] / 1000000).astype(str) + "M"
    
    race_cols = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'BDP', 'E3', 'GW', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
    available_races = [k for k in race_cols if k in merged_df.columns]
    
    koers_stat_map = {
        'OHN': 'COB', 'KBK': 'SPR', 'SB': 'HLL', 'PN': 'HLL', 'TA': 'HLL',
        'MSR': 'SPR', 'BDP': 'SPR', 'E3': 'COB', 'GW': 'SPR', 'DDV': 'COB',
        'RVV': 'COB', 'SP': 'SPR', 'PR': 'COB', 'BP': 'HLL', 'AGR': 'HLL',
        'WP': 'HLL', 'LBL': 'HLL'
    }

    # Scorito_EV berekenen
    merged_df['Scorito_EV'] = 0.0
    for koers in available_races:
        stat_nodig = koers_stat_map.get(koers, 'AVG') 
        merged_df['Scorito_EV'] += merged_df[koers] * ((merged_df[stat_nodig] / 100)**4 * 100)
    
    return merged_df, available_races, koers_stat_map

# --- INITIALISATIE ---
df, race_cols, koers_mapping = load_and_merge_data()

if "rider_multiselect" not in st.session_state:
    st.session_state.rider_multiselect = []

# --- SOLVER FUNCTIE ---
def solve_knapsack(dataframe, total_budget, min_budget, max_riders, force_list, exclude_list):
    prob = pulp.LpProblem("Scorito_Solver", pulp.LpMaximize)
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe.index, cat='Binary')
    
    prob += pulp.lpSum([dataframe.loc[i, 'Scorito_EV'] * rider_vars[i] for i in dataframe.index])
    prob += pulp.lpSum([rider_vars[i] for i in dataframe.index]) == max_riders
    prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) <= total_budget
    prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) >= min_budget
    
    for i in dataframe.index:
        if dataframe.loc[i, 'Renner'] in force_list: prob += rider_vars[i] == 1
        if dataframe.loc[i, 'Renner'] in exclude_list: prob += rider_vars[i] == 0
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if pulp.LpStatus[prob.status] == 'Optimal':
        return [dataframe.loc[i, 'Display'] for i in dataframe.index if rider_vars[i].varValue > 0.5]
    return None

# --- UI ---
st.title("🏆 Scorito Klassiekers 2026 AI Solver")

col_settings, col_selection = st.columns([1, 2], gap="large")

with col_settings:
    st.header("⚙️ Instellingen")
    max_renners = st.number_input("Aantal Renners", value=20)
    max_budget = st.number_input("Max Budget", value=45000000, step=500000)
    min_budget = st.number_input("Min Budget", value=44000000, step=500000)
    
    st.divider()
    force_display = st.multiselect("🔒 Forceer:", options=df['Display'].tolist())
    exclude_display = st.multiselect("❌ Sluit uit:", options=[r for r in df['Display'].tolist() if r not in force_display])
    
    forced_riders = df[df['Display'].isin(force_display)]['Renner'].tolist()
    excluded_riders = df[df['Display'].isin(exclude_display)]['Renner'].tolist()

    if st.button("🚀 Genereer Team", type="primary", use_container_width=True):
        result = solve_knapsack(df, max_budget, min_budget, max_renners, forced_riders, excluded_riders)
        if result:
            st.session_state.rider_multiselect = result
            st.rerun()
        else:
            st.error("Geen oplossing. Verlaag 'Min Budget' of forceer minder dure renners.")

with col_selection:
    st.header("1. Jouw Selectie")
    st.multiselect("Team:", options=df['Display'].tolist(), key="rider_multiselect")

# --- DASHBOARD ---
if st.session_state.rider_multiselect:
    current_df = df[df['Display'].isin(st.session_state.rider_multiselect)].copy()
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Budget over", f"€ {max_budget - current_df['Prijs'].sum():,.0f}")
    m2.metric("Renners", f"{len(current_df)} / {max_renners}")
    m3.metric("Team EV", f"{current_df['Scorito_EV'].sum():.0f}")

    st.header("🗓️ Deelnames Matrix")
    matrix = current_df[['Renner'] + race_cols].set_index('Renner')
    matrix = matrix.applymap(lambda x: '✅' if x == 1 else '-')
    st.dataframe(matrix, use_container_width=True)

    st.header("🔄 Finetuner")
    edit_df = current_df[['Renner', 'Display', 'Prijs', 'Scorito_EV']].copy()
    edit_df.insert(0, 'Vervang', False)
    edited = st.data_editor(edit_df, hide_index=True, use_container_width=True, disabled=["Renner", "Display", "Prijs", "Scorito_EV"])
    
    if st.button("🔄 Vervang geselecteerden"):
        to_keep = edited[edited['Vervang'] == False]['Renner'].tolist()
        to_replace = edited[edited['Vervang'] == True]['Renner'].tolist()
        new_team = solve_knapsack(df, max_budget, 0, max_renners, list(set(forced_riders + to_keep)), list(set(excluded_riders + to_replace)))
        if new_team:
            st.session_state.rider_multiselect = new_team
            st.rerun()

    st.header("🥇 Kopman Advies")
    kopman_lijst = []
    for koers in race_cols:
        starters = current_df[current_df[koers] == 1]
        if not starters.empty:
            stat = koers_mapping.get(koers, 'AVG')
            top = starters.sort_values(by=[stat, 'AVG'], ascending=False)['Renner'].tolist()
            kopman_lijst.append({
                "Koers": koers, "Type": stat, 
                "K1 (3x)": top[0] if len(top)>0 else "-", 
                "K2 (2.5x)": top[1] if len(top)>1 else "-", 
                "K3 (2x)": top[2] if len(top)>2 else "-"
            })
    st.dataframe(pd.DataFrame(kopman_lijst), use_container_width=True, hide_index=True)
