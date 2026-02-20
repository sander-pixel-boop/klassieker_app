import streamlit as st
import pandas as pd
import pulp
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Klassiekers Solver 2026", layout="wide", page_icon="🚴‍♂️")

# --- DATA LADEN & MERGEN ---
@st.cache_data
def load_and_merge_data():
    # Lees bestanden in
    # Let op: als je renners_stats.csv als komma-gescheiden hebt opgeslagen, verander sep='\t' naar sep=','
    df_prog = pd.read_csv("bron_startlijsten.csv")
    df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
    
    # Zorg dat de naamkolom in stats 'Renner' heet
    if 'Naam' in df_stats.columns:
        df_stats = df_stats.rename(columns={'Naam': 'Renner'})
    
    # 1. Haal unieke namen op
    short_names = df_prog['Renner'].unique()
    full_names = df_stats['Renner'].unique()
    
    # 2. Maak een fuzzy mapping dictionary
    name_mapping = {}
    
    # Handmatige overrides voor afkortingen of namen die fout kunnen gaan
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
            # Fuzzy match op basis van token_set_ratio (bijv. "Pogacar" -> "Tadej Pogačar")
            best_match, score = process.extractOne(short, full_names, scorer=fuzz.token_set_ratio)
            name_mapping[short] = best_match

    # 3. Voer de mapping uit op de startlijst
    df_prog['Renner_Full'] = df_prog['Renner'].map(name_mapping)
    
    # 4. Los dubbele namen op d.m.v. Prijs
    df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 1500000), 'Renner_Full'] = 'Florian Vermeersch'
    df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Gianni Vermeersch'
    df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] == 4500000), 'Renner_Full'] = 'Mads Pedersen'
    df_prog.loc[(df_prog['Renner'] == 'Pedersen') & (df_prog['Prijs'] == 500000), 'Renner_Full'] = 'Rasmus Søjberg Pedersen'
    df_prog.loc[(df_prog['Renner'] == 'Martinez') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Lenny Martinez'
    df_prog.loc[(df_prog['Renner'] == 'Oliveira') & (df_prog['Prijs'] == 1000000), 'Renner_Full'] = 'Rui Oliveira'

    # 5. Merge datasets op basis van de volledige naam
    merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='inner')
    
    # Opschonen van kolommen na merge
    if 'Renner_x' in merged_df.columns:
        merged_df = merged_df.drop(columns=['Renner_x', 'Renner_y'])
    merged_df = merged_df.rename(columns={'Renner_Full': 'Renner'})
    
    # Maak Display kolom voor de Multiselect
    merged_df['Display'] = merged_df['Renner'] + " - " + (merged_df['Prijs'] / 1000000).astype(str) + "M"
    
    # Haal de lijst met koersen op
    koersen = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'RvV', 'E3', 'IFF', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
    
    # Bereken totaal aantal gereden koersen en een basis Expected Value (EV)
    merged_df['Total_Races'] = merged_df[koersen].sum(axis=1)
    merged_df['EV'] = ((merged_df['AVG'] + merged_df['COB'] + merged_df['HLL'] + merged_df['SPR']) / 4) * merged_df['Total_Races']
    
    return merged_df, koersen

# --- ERROR HANDLING DATA ---
try:
    df, race_cols = load_and_merge_data()
except Exception as e:
    st.error(f"⚠️ Fout bij inladen data. Check of 'bron_startlijsten.csv' en 'renners_stats.csv' in dezelfde map staan. Details: {e}")
    st.stop()

# --- AI SOLVER FUNCTIE ---
def solve_knapsack(dataframe, total_budget, max_riders):
    prob = pulp.LpProblem("Klassieker_Team", pulp.LpMaximize)
    
    # Variabelen per renner (0 of 1)
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe['Renner'], cat='Binary')
    
    # DOELFUNCTIE: Maximaliseer de EV
    prob += pulp.lpSum([dataframe.loc[dataframe['Renner'] == r, 'EV'].values[0] * rider_vars[r] for r in dataframe['Renner']])
    
    # RESTRICTIES
    prob += pulp.lpSum([rider_vars[r] for r in dataframe['Renner']]) == max_riders, "Max_Renners"
    prob += pulp.lpSum([dataframe.loc[dataframe['Renner'] == r, 'Prijs'].values[0] * rider_vars[r] for r in dataframe['Renner']]) <= total_budget, "Max_Budget"
    
    # LOS OP
    prob.solve()
    
    if pulp.LpStatus[prob.status] == 'Optimal':
        # Retourneer de 'Display' namen zodat we die direct in de UI in de multiselect kunnen schieten
        optimal_display_names = [dataframe.loc[dataframe['Renner'] == r, 'Display'].values[0] for r in dataframe['Renner'] if rider_vars[r].varValue == 1]
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
    
    st.info("De AI selecteert het team op basis van een mix van gereden programma's en algemene statistieken (Kassei, Heuvel, Sprint, AVG).")
    
    if st.button("🧠 Genereer Optimaal Team", type="primary", use_container_width=True):
        with st.spinner('Bezig met kraken van de code...'):
            opt_team = solve_knapsack(df, budget, max_renners)
            if opt_team:
                st.session_state.selected_riders = opt_team
                st.success("Optimaal team berekend!")
            else:
                st.error("Kon geen optimaal team vinden met deze restricties.")

with col_ui2:
    st.header("1. Jouw Selectie")
    
    # Session state initiëren
    if 'selected_riders' not in st.session_state:
        st.session_state.selected_riders = []

    # De multiselect balk: is te vullen via de Solver, of handmatig!
    selected_display = st.multiselect(
        "Zoek en selecteer je renners of laat de AI het doen:", 
        options=df['Display'].tolist(),
        default=st.session_state.selected_riders,
        max_selections=max_renners,
        key="rider_multiselect"
    )
    
    # Update de session state als je handmatig dingen verwijdert/toevoegt
    st.session_state.selected_riders = selected_display

# --- RESULTATEN WEERGAVE ---
if st.session_state.selected_riders:
    selected_df = df[df['Display'].isin(st.session_state.selected_riders)].copy()
    
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
    
    # Kies welke kolommen je wilt zien in het eindoverschot
    display_cols = ['Renner', 'Prijs', 'Total_Races', 'EV', 'AVG', 'COB', 'HLL', 'SPR'] + race_cols
    
    # Laat de tabel zien (netjes gesorteerd op prijs)
    st.dataframe(
        selected_df[display_cols].sort_values(by='Prijs', ascending=False).reset_index(drop=True), 
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Kies minimaal 1 renner in de selectiebalk of klik op 'Genereer Optimaal Team' om te beginnen.")
