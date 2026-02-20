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
        # 1. Lees startlijsten
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', on_bad_lines='skip')
        
        # Gebruikersregel: 0.8M is altijd 750000
        df_prog.loc[df_prog['Prijs'] == 800000, 'Prijs'] = 750000
        
        # 2. Lees stats
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        
        # 3. Fuzzy Matching
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
        
        # Dubbele namen correcties
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 1500000), 'Renner_Full'] = 'Florian Vermeersch'
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Gianni Vermeersch'
        df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] == 4500000), 'Renner_Full'] = 'Mads Pedersen'
        df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] == 500000), 'Renner_Full'] = 'Rasmus Søjberg Pedersen'

        # 4. Merge
        merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='inner')
        
        if 'Renner_x' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Renner_x', 'Renner_y'])
        merged_df = merged_df.rename(columns={'Renner_Full': 'Renner'})
        merged_df = merged_df.drop_duplicates(subset=['Renner', 'Prijs'])
        
        # 5. EV Berekening
        race_cols = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'BDP', 'E3', 'GW', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
        available_races = [k for k in race_cols if k in merged_df.columns]
        
        koers_stat_map = {
            'OHN': 'COB', 'KBK': 'SPR', 'SB': 'HLL', 'PN': 'HLL', 'TA': 'HLL',
            'MSR': 'SPR', 'BDP': 'SPR', 'E3': 'COB', 'GW': 'SPR', 'DDV': 'COB',
            'RVV': 'COB', 'SP': 'SPR', 'PR': 'COB', 'BP': 'HLL', 'AGR': 'HLL',
            'WP': 'HLL', 'LBL': 'HLL'
        }

        merged_df['Scorito_EV'] = 0.0
        for koers in available_races:
            stat_nodig = koers_stat_map.get(koers, 'AVG')
            # Veiligheid: zorg dat de stat een getal is, vervang NaN door 0
            merged_df[stat_nodig] = pd.to_numeric(merged_df[stat_nodig], errors='coerce').fillna(0)
            merged_df[koers] = pd.to_numeric(merged_df[koers], errors='coerce').fillna(0)
            
            merged_df['Scorito_EV'] += merged_df[koers] * ((merged_df[stat_nodig] / 100)**4 * 100)

        # Laatste check: verwijder elke rij waar Scorito_EV nog steeds NaN is
        merged_df = merged_df.dropna(subset=['Scorito_EV', 'Prijs'])
        merged_df['Display'] = merged_df['Renner'] + " - " + (merged_df['Prijs'] / 1000000).astype(str) + "M"
        
        return merged_df, available_races, koers_stat_map

    except Exception as e:
        st.error(f"Fout in dataverwerking: {e}")
        return pd.DataFrame(), [], {}

# --- INITIALISATIE ---
df, race_cols, koers_mapping = load_and_merge_data()

if df.empty:
    st.warning("De database is leeg. Controleer je CSV-bestanden op GitHub.")
    st.stop()

if "rider_multiselect" not in st.session_state:
    st.session_state.rider_multiselect = []

# --- SOLVER FUNCTIE ---
def solve_knapsack(dataframe, total_budget, min_budget, max_riders, force_list, exclude_list):
    # Filter eventuele NaN prijzen of EV's voor de zekerheid
    clean_df = dataframe.dropna(subset=['Scorito_EV', 'Prijs']).copy()
    
    prob = pulp.LpProblem("Scorito_Solver", pulp.LpMaximize)
    rider_vars = pulp.LpVariable.dicts("Riders", clean_df.index, cat='Binary')
    
    # Doel
    prob += pulp.lpSum([clean_df.loc[i, 'Scorito_EV'] * rider_vars[i] for i in clean_df.index])
    
    # Restricties
    prob += pulp.lpSum([rider_vars[i] for i in clean_df.index]) == max_riders
    prob += pulp.lpSum([clean_df.loc[i, 'Prijs'] * rider_vars[i] for i in clean_df.index]) <= total_budget
    prob += pulp.lpSum([clean_df.loc[i, 'Prijs'] * rider_vars[i] for i in clean_df.index]) >= min_budget
    
    for i in clean_df.index:
        if clean_df.loc[i, 'Renner'] in force_list: prob += rider_vars[i] == 1
        if clean_df.loc[i, 'Renner'] in exclude_list: prob += rider_vars[i] == 0
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if pulp.LpStatus[prob.status] == 'Optimal':
        return [clean_df.loc[i, 'Display'] for i in clean_df.index if rider_vars[i].varValue > 0.5]
    return None

# --- UI ---
st.title("🏆 Scorito Klassiekers 2026 AI Solver")

col_settings, col_selection = st.columns([1, 2], gap="large")

with col_settings:
    st.header("⚙️ Instellingen")
    max_renners = st.number_input("Aantal Renners", value=20)
    max_budget = st.number_input("Max Budget", value=45000000, step=500000)
    min_budget = st.number_input("Min Budget", value=43000000, step=500000)
    
    st.divider()
    force_display = st.multiselect("🔒 Forceer:", options=df['Display'].tolist())
    exclude_display = st.multiselect("❌ Sluit uit:", options=[r for r in df['Display'].tolist() if r not in force_display])
    
    forced_riders = df[df['Display'].isin(force_display)]['Renner'].tolist()
    excluded_riders = df[df['Display'].isin(exclude_display)]['Renner'].tolist()

    if st.button("🚀 Bereken Team", type="primary", use_container_width=True):
        result = solve_knapsack(df, max_budget, min_budget, max_renners, forced_riders, excluded_riders)
        if result:
            st.session_state.rider_multiselect = result
            st.rerun()
        else:
            st.error("Geen oplossing. Probeer het 'Min Budget' te verlagen.")

with col_selection:
    st.header("1. Jouw Selectie")
    st.multiselect("Geselecteerd team:", options=df['Display'].tolist(), key="rider_multiselect")

# --- DASHBOARD ---
if st.session_state.rider_multiselect:
    current_df = df[df['Display'].isin(st.session_state.rider_multiselect)].copy()
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Resterend Budget", f"€ {max_budget - current_df['Prijs'].sum():,.0f}")
    m2.metric("Aantal", f"{len(current_df)} / {max_renners}")
    m3.metric("Verwachte Punten", f"{current_df['Scorito_EV'].sum():.0f}")

    # Matrix
    st.header("🗓️ Startlijst Matrix")
    matrix = current_df[['Renner'] + race_cols].set_index('Renner')
    matrix = matrix.applymap(lambda x: '✅' if x == 1 else '-')
    st.dataframe(matrix, use_container_width=True)

    # Finetuner
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

    # Kopman advies
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
    st.table(pd.DataFrame(kopman_lijst))
