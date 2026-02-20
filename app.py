import streamlit as st
import pandas as pd
import pulp
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Scorito Klassiekers Solver 2026", layout="wide", page_icon="🚴‍♂️")

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
    
    merged_df = merged_df.drop_duplicates(subset=['Renner'])
    merged_df['Display'] = merged_df['Renner'] + " - " + (merged_df['Prijs'] / 1000000).astype(str) + "M"
    
    koersen = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'RvV', 'E3', 'IFF', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
    beschikbare_koersen = [k for k in koersen if k in merged_df.columns]
    
    koers_stat_map = {
        'OHN': 'COB', 'KBK': 'SPR', 'SB': 'HLL', 'PN': 'HLL', 'TA': 'HLL',
        'MSR': 'SPR', 'RvV': 'COB', 'E3': 'COB', 'IFF': 'SPR', 'DDV': 'COB',
        'RVV': 'COB', 'SP': 'SPR', 'PR': 'COB', 'BP': 'HLL', 'AGR': 'HLL',
        'WP': 'HLL', 'LBL': 'HLL'
    }

    merged_df['Scorito_EV'] = 0.0
    merged_df['Total_Races'] = merged_df[beschikbare_koersen].sum(axis=1)

    for koers in beschikbare_koersen:
        stat_nodig = koers_stat_map.get(koers, 'AVG') 
        verwachte_koers_punten = (merged_df[stat_nodig] / 100)**4 * 100
        merged_df['Scorito_EV'] += merged_df[koers] * verwachte_koers_punten
    
    return merged_df, beschikbare_koersen, koers_stat_map

try:
    df, race_cols, koers_mapping = load_and_merge_data()
except Exception as e:
    st.error(f"⚠️ Fout bij inladen data. Details: {e}")
    st.stop()

# --- AI SOLVER FUNCTIE ---
def solve_knapsack(dataframe, total_budget, min_budget, max_riders, force_list, exclude_list):
    prob = pulp.LpProblem("Scorito_Klassieker_Team", pulp.LpMaximize)
    
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe['Renner'], cat='Binary')
    
    prob += pulp.lpSum([dataframe.loc[dataframe['Renner'] == r, 'Scorito_EV'].values[0] * rider_vars[r] for r in dataframe['Renner']])
    
    prob += pulp.lpSum([rider_vars[r] for r in dataframe['Renner']]) == max_riders, "Max_Renners"
    prob += pulp.lpSum([dataframe.loc[dataframe['Renner'] == r, 'Prijs'].values[0] * rider_vars[r] for r in dataframe['Renner']]) <= total_budget, "Max_Budget"
    prob += pulp.lpSum([dataframe.loc[dataframe['Renner'] == r, 'Prijs'].values[0] * rider_vars[r] for r in dataframe['Renner']]) >= min_budget, "Min_Budget"
    
    for r in force_list:
        if r in rider_vars:
            prob += rider_vars[r] == 1
            
    for r in exclude_list:
        if r in rider_vars:
            prob += rider_vars[r] == 0
    
    prob.solve()
    
    if pulp.LpStatus[prob.status] == 'Optimal':
        optimal_display_names = [
            dataframe.loc[dataframe['Renner'] == r, 'Display'].values[0] 
            for r in dataframe['Renner'] 
            if rider_vars[r].varValue is not None and rider_vars[r].varValue > 0.5
        ]
        return optimal_display_names
    else:
        return []

# --- UI OPBOUW ---
st.title("🏆 Scorito Klassiekers 2026 - AI Solver")

col_ui1, col_ui2 = st.columns([1, 2], gap="large")

with col_ui1:
    st.header("⚙️ Instellingen & AI")
    max_renners = st.number_input("Aantal Renners", value=20, min_value=1, max_value=25)
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        max_budget = st.number_input("Max Budget", value=45000000, step=500000)
    with col_b2:
        min_budget = st.number_input("Min Budget", value=44500000, step=500000)
    
    st.divider()
    st.subheader("Sturing Algoritme")
    force_display = st.multiselect("🔒 Forceer renners (Verplicht in AI team):", options=df['Display'].tolist())
    exclude_options = [r for r in df['Display'].tolist() if r not in force_display]
    exclude_display = st.multiselect("❌ Sluit renners uit (Genegeerd door AI):", options=exclude_options)
    
    # Bewaar de ruwe namen voor de solver
    forced_riders = df[df['Display'].isin(force_display)]['Renner'].tolist()
    excluded_riders = df[df['Display'].isin(exclude_display)]['Renner'].tolist()

    if st.button("🧠 Genereer Scorito Team", type="primary", use_container_width=True):
        with st.spinner('Bezig met het berekenen van verwachte kopman-punten...'):
            opt_team = solve_knapsack(df, max_budget, min_budget, max_renners, forced_riders, excluded_riders)
            if opt_team:
                st.session_state.rider_multiselect = opt_team
                st.rerun() 
            else:
                st.error("Kon geen geldig team vinden. Probeer het 'Min Budget' te verlagen of minder renners te forceren.")

with col_ui2:
    st.header("1. Jouw Selectie")
    
    if "rider_multiselect" not in st.session_state:
        st.session_state.rider_multiselect = []

    selected_display = st.multiselect(
        "Zoek en selecteer je renners of gebruik de AI knop:", 
        options=df['Display'].tolist(),
        max_selections=max_renners,
        key="rider_multiselect"
    )

# --- RESULTATEN WEERGAVE ---
if st.session_state.rider_multiselect:
    selected_df = df[df['Display'].isin(st.session_state.rider_multiselect)].copy()
    
    spent = selected_df['Prijs'].sum()
    remaining = max_budget - spent
    total_ev = selected_df['Scorito_EV'].sum()
    
    st.divider()
    st.header("2. Budget & Overzicht")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Geselecteerd", f"{len(selected_df)} / {max_renners}")
    col_m2.metric("Uitgegeven", f"€ {spent:,.0f}".replace(",", "."))
    
    if remaining < 0:
        col_m3.metric("Resterend", f"€ {remaining:,.0f}".replace(",", "."), delta="- Over budget", delta_color="inverse")
    else:
        col_m3.metric("Resterend", f"€ {remaining:,.0f}".replace(",", "."))
        
    col_m4.metric("Team EV (Verwachte Pts)", f"{total_ev:.0f}")

    # --- NIEUW: FINETUNE HET TEAM MET CHECKBOXES ---
    st.divider()
    st.header("🔄 3. Finetune je Team (Vervang Renners)")
    st.write("Ben je het niet eens met bepaalde keuzes van de AI? Vink hieronder renners aan die je uit het team wilt halen. Klik daarna op 'Vervang Geselecteerde Renners'. De AI behoudt de niet-aangevinkte renners en zoekt de beste opvulling met je resterende budget.")
    
    # Maak een interactieve dataframe
    edit_df = selected_df[['Renner', 'Display', 'Prijs', 'Scorito_EV']].copy()
    edit_df.insert(0, 'Vervang', False) # Voeg een checkbox kolom toe
    
    edited_df = st.data_editor(
        edit_df.sort_values(by='Prijs', ascending=False),
        column_config={
            "Vervang": st.column_config.CheckboxColumn("Vervang?", default=False),
            "Prijs": st.column_config.NumberColumn(format="€ %d"),
            "Scorito_EV": st.column_config.NumberColumn(format="%.1f")
        },
        disabled=["Renner", "Display", "Prijs", "Scorito_EV"],
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("🔄 Vervang Geselecteerde Renners", type="secondary"):
        # Bepaal wie we houden en wie eruit moet
        riders_to_keep = edited_df[edited_df['Vervang'] == False]['Renner'].tolist()
        riders_to_replace = edited_df[edited_df['Vervang'] == True]['Renner'].tolist()
        
        if len(riders_to_replace) == 0:
            st.warning("Je hebt niemand aangevinkt om te vervangen.")
        else:
            with st.spinner('Nieuwe alternatieven berekenen...'):
                # Combineer de renners die we willen houden met eventuele harde 'forces' uit het zijmenu
                combined_force = list(set(forced_riders + riders_to_keep))
                # Combineer de te vervangen renners met de uitsluitingen uit het zijmenu
                combined_exclude = list(set(excluded_riders + riders_to_replace))
                
                # We zetten min_budget op 0 tijdens het finetunen, anders loopt de AI soms vast bij specifieke vervangingen
                new_team = solve_knapsack(df, max_budget, 0, max_renners, combined_force, combined_exclude)
                
                if new_team:
                    st.session_state.rider_multiselect = new_team
                    st.rerun()
                else:
                    st.error("Kon de renners niet vervangen zonder het budget te overschrijden of restricties te schenden.")

    # --- KOPMAN & KOERS OVERZICHT ---
    st.divider()
    st.header("4. Programma & Kopmannen Advies")
    st.write("Automatisch berekende kopmannen per koers op basis van de specifieke statistiek (Kassei, Heuvel of Sprint).")
    
    kopman_data = []
    
    for koers in race_cols:
        starters = selected_df[selected_df[koers] == 1]
        
        if not starters.empty:
            stat_nodig = koers_mapping.get(koers, 'AVG')
            starters_sorted = starters.sort_values(by=[stat_nodig, 'AVG'], ascending=[False, False])
            namenlijst = starters_sorted['Renner'].tolist()
            
            kopman_1 = namenlijst[0] if len(namenlijst) > 0 else "-"
            kopman_2 = namenlijst[1] if len(namenlijst) > 1 else "-"
            kopman_3 = namenlijst[2] if len(namenlijst) > 2 else "-"
            overige_renners = ", ".join(namenlijst[3:]) if len(namenlijst) > 3 else "-"
            
            kopman_data.append({
                "Koers": koers,
                "Type": stat_nodig,
                "Aantal": len(namenlijst),
                "Kopman 1 (3x)": kopman_1,
                "Kopman 2 (2.5x)": kopman_2,
                "Kopman 3 (2x)": kopman_3,
                "Overige Renners": overige_renners
            })
    
    if kopman_data:
        df_kopmannen = pd.DataFrame(kopman_data)
        st.dataframe(df_kopmannen, use_container_width=True, hide_index=True)

else:
    st.info("Kies minimaal 1 renner in de selectiebalk of klik op 'Genereer Scorito Team' om te beginnen.")
