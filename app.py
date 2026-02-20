import streamlit as st
import pandas as pd
import pulp
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Klassiekers Solver 2026", layout="wide", page_icon="🚴‍♂️")

# --- DATA LADEN & MERGEN ---
@st.cache_data
def load_and_merge_data():
    df_prog = pd.read_csv("bron_startlijsten.csv")
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
    
    # Forceer specifieke dubbele namen correct
    df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 1500000), 'Renner_Full'] = 'Florian Vermeersch'
    df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Gianni Vermeersch'
    df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] == 4500000), 'Renner_Full'] = 'Mads Pedersen'
    df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] == 500000), 'Renner_Full'] = 'Rasmus Søjberg Pedersen'
    df_prog.loc[(df_prog['Renner'] == 'Martinez') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Lenny Martinez'
    df_prog.loc[(df_prog['Renner'] == 'Oliveira') & (df_prog['Prijs'] == 1000000), 'Renner_Full'] = 'Rui Oliveira'

    merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='inner')
    
    if 'Renner_x' in merged_df.columns:
        merged_df = merged_df.drop(columns=['Renner_x', 'Renner_y'])
    merged_df = merged_df.rename(columns={'Renner_Full': 'Renner'})
    
    # CRUCIALE FIX: Verwijder duplicaten zodat het algoritme geen namen dubbel telt
    merged_df = merged_df.drop_duplicates(subset=['Renner'])
    
    merged_df['Display'] = merged_df['Renner'] + " - " + (merged_df['Prijs'] / 1000000).astype(str) + "M"
    
    koersen = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'RvV', 'E3', 'IFF', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
    beschikbare_koersen = [k for k in koersen if k in merged_df.columns]
    
    merged_df['Total_Races'] = merged_df[beschikbare_koersen].sum(axis=1)
    merged_df['EV'] = ((merged_df['AVG'] + merged_df['COB'] + merged_df['HLL'] + merged_df['SPR']) / 4) * merged_df['Total_Races']
    
    return merged_df, beschikbare_koersen

try:
    df, race_cols = load_and_merge_data()
except Exception as e:
    st.error(f"⚠️ Fout bij inladen data. Details: {e}")
    st.stop()

# --- AI SOLVER FUNCTIE ---
def solve_knapsack(dataframe, total_budget, max_riders, force_list, exclude_list):
    prob = pulp.LpProblem("Klassieker_Team", pulp.LpMaximize)
    
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe['Renner'], cat='Binary')
    
    # Doelfunctie
    prob += pulp.lpSum([dataframe.loc[dataframe['Renner'] == r, 'EV'].values[0] * rider_vars[r] for r in dataframe['Renner']])
    
    # Basis restricties
    prob += pulp.lpSum([rider_vars[r] for r in dataframe['Renner']]) == max_riders, "Max_Renners"
    prob += pulp.lpSum([dataframe.loc[dataframe['Renner'] == r, 'Prijs'].values[0] * rider_vars[r] for r in dataframe['Renner']]) <= total_budget, "Max_Budget"
    
    # Forceer restricties (moet 1 zijn)
    for r in force_list:
        if r in rider_vars:
            prob += rider_vars[r] == 1
            
    # Uitsluit restricties (moet 0 zijn)
    for r in exclude_list:
        if r in rider_vars:
            prob += rider_vars[r] == 0
    
    prob.solve()
    
    if pulp.LpStatus[prob.status] == 'Optimal':
        # CRUCIALE FIX: varValue > 0.5 in plaats van == 1 om afrondingsfouten te voorkomen
        optimal_display_names = [
            dataframe.loc[dataframe['Renner'] == r, 'Display'].values[0] 
            for r in dataframe['Renner'] 
            if rider_vars[r].varValue is not None and rider_vars[r].varValue > 0.5
        ]
        return optimal_display_names
    else:
        return []

# --- UI OPBOUW ---
st.title("🤖 Klassiekers 2026 - AI Solver & Team Builder")

col_ui1, col_ui2 = st.columns([1, 2], gap="large")

with col_ui1:
    st.header("⚙️ Instellingen & Solver")
    max_renners = st.number_input("Max Aantal Renners", value=20, min_value=1, max_value=25)
    budget = st.number_input("Totaal Budget", value=45000000, step=500000)
    
    st.divider()
    st.subheader("Sturing Algoritme")
    force_display = st.multiselect("🔒 Forceer deze renners (AI móét deze kiezen):", options=df['Display'].tolist())
    
    exclude_options = [r for r in df['Display'].tolist() if r not in force_display]
    exclude_display = st.multiselect("❌ Sluit deze renners uit (AI mag deze niet kiezen):", options=exclude_options)
    
    forced_riders = df[df['Display'].isin(force_display)]['Renner'].tolist()
    excluded_riders = df[df['Display'].isin(exclude_display)]['Renner'].tolist()

    if st.button("🧠 Genereer Optimaal Team", type="primary", use_container_width=True):
        with st.spinner('Bezig met kraken van de code...'):
            opt_team = solve_knapsack(df, budget, max_renners, forced_riders, excluded_riders)
            if opt_team:
                st.session_state.rider_multiselect = opt_team
                st.rerun() 
            else:
                st.error("Kon geen optimaal team vinden. Je hebt te dure renners geforceerd, of het budget is te laag.")

with col_ui2:
    st.header("1. Jouw Selectie")
    
    if "rider_multiselect" not in st.session_state:
        st.session_state.rider_multiselect = []

    selected_display = st.multiselect(
        "Zoek en selecteer je renners of laat de AI het doen:", 
        options=df['Display'].tolist(),
        max_selections=max_renners,
        key="rider_multiselect"
    )

# --- RESULTATEN WEERGAVE ---
if st.session_state.rider_multiselect:
    selected_df = df[df['Display'].isin(st.session_state.rider_multiselect)].copy()
    
    spent = selected_df['Prijs'].sum()
    remaining = budget - spent
    
    st.divider()
    st.header("2. Budget & Overzicht")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Geselecteerd", f"{len(selected_df)} / {max_renners}")
    col_m2.metric("Uitgegeven", f"€ {spent:,.0f}".replace(",", "."))
    
    if remaining < 0:
        col_m3.metric("Resterend", f"€ {remaining:,.0f}".replace(",", "."), delta="- Over budget", delta_color="inverse")
    else:
        col_m3.metric("Resterend", f"€ {remaining:,.0f}".replace(",", "."))

    st.subheader("Renners Data")
    
    display_cols = ['Renner', 'Prijs', 'Total_Races', 'EV', 'AVG', 'COB', 'HLL', 'SPR'] + race_cols
    
    st.dataframe(
        selected_df[display_cols].sort_values(by='Prijs', ascending=False).reset_index(drop=True), 
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Kies minimaal 1 renner in de selectiebalk of klik op 'Genereer Optimaal Team' om te beginnen.")
