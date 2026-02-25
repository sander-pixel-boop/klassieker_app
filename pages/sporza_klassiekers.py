import streamlit as st
import pandas as pd
import pulp
import json

# --- CONFIGURATIE ---
st.set_page_config(page_title="Sporza Wielermanager (WIP)", layout="wide", page_icon="🦁")

st.title("🦁 Sporza Wielermanager - Team Builder")

# --- WIP MELDING ---
st.warning("🚧 **WORK IN PROGRESS (WIP)** 🚧\n\nDeze module is momenteel in aanbouw. We wachten op de dataset met de officiële Sporza-prijzen en de juiste ploegindelingen voor dit jaar.")

st.markdown("""
**Waarom Sporza anders is dan Scorito:**
* Budget van **€120 miljoen** in plaats van €45 miljoen.
* Exact **20 renners** in je selectie (12 starters, 8 in de bus).
* Maximaal **4 renners per ploeg** (dit vereist een extra regel in het wiskundige algoritme).
* Punten voor koersen hebben een andere weging (Monument = 125pt, WT = 100pt, etc.).
* Teampunten (10 bonuspunten voor ploegmaats van de winnaar).
""")

st.divider()

# --- DATA UPLOADER (Voor later) ---
st.sidebar.header("📂 1. Data Inladen")
st.sidebar.markdown("Upload hier je Sporza-dataset (.csv) zodra je deze hebt.")

uploaded_file = st.sidebar.file_uploader("Upload Sporza Data", type=["csv"])

if "sporza_data" not in st.session_state:
    st.session_state.sporza_data = None

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        required_cols = ['Renner', 'Ploeg', 'Prijs', 'EV']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.sidebar.error(f"⚠️ Let op! De dataset mist deze kolommen: {', '.join(missing_cols)}.")
        else:
            st.session_state.sporza_data = df
            st.sidebar.success("✅ Data succesvol geladen!")
    except Exception as e:
        st.sidebar.error(f"Fout bij inladen: {e}")

# --- SOLVER ALGORITME (SPORZA REGELS) ---
def solve_sporza_team(dataframe, budget, num_riders, max_per_team, force_in, force_out):
    prob = pulp.LpProblem("Sporza_Solver", pulp.LpMaximize)
    
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe.index, cat='Binary')
    
    prob += pulp.lpSum([dataframe.loc[i, 'EV'] * rider_vars[i] for i in dataframe.index])
    prob += pulp.lpSum([rider_vars[i] for i in dataframe.index]) == num_riders
    prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) <= budget
    
    teams = dataframe['Ploeg'].unique()
    for ploeg in teams:
        team_indices = dataframe[dataframe['Ploeg'] == ploeg].index
        prob += pulp.lpSum([rider_vars[i] for i in team_indices]) <= max_per_team
        
    for i in dataframe.index:
        renner = dataframe.loc[i, 'Renner']
        if renner in force_in: prob += rider_vars[i] == 1
        if renner in force_out: prob += rider_vars[i] == 0
            
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=15))
    
    if pulp.LpStatus[prob.status] == 'Optimal':
        selected_indices = [i for i in dataframe.index if rider_vars[i].varValue > 0.5]
        return dataframe.loc[selected_indices]
    else:
        return None

# --- HOOFDSCHERM ---
if st.session_state.sporza_data is not None:
    df = st.session_state.sporza_data.copy()
    
    if "sporza_team" not in st.session_state:
        st.session_state.sporza_team = []
        
    tab1, tab2 = st.tabs(["🚀 Team Berekenen", "📋 Renner Database"])
    
    with tab1:
        col1, col2 = st.columns([1, 2], gap="large")
        
        with col1:
            st.header("⚙️ Instellingen")
            budget = st.number_input("Totaal Budget", value=120.0, step=1.0)
            aantal = st.number_input("Aantal Renners", value=20, min_value=1)
            max_ploeg = st.number_input("Max per Ploeg", value=4, min_value=1)
            
            st.divider()
            st.markdown("**Handmatig Forceren**")
            force_in = st.multiselect("🟢 Moet in het team:", options=df['Renner'].tolist())
            force_out = st.multiselect("🔴 Mag NIET in het team:", options=[r for r in df['Renner'].tolist() if r not in force_in])
            
            if st.button("🚀 Bereken Sporza Team", type="primary", use_container_width=True):
                optimal_team_df = solve_sporza_team(df, budget, aantal, max_ploeg, force_in, force_out)
                
                if optimal_team_df is not None:
                    st.session_state.sporza_team = optimal_team_df['Renner'].tolist()
                    st.rerun()
                else:
                    st.error("Geen oplossing mogelijk! Probeer minder dure renners te forceren of check de ploegenlimiet.")

        with col2:
            st.header("🏆 Jouw Sporza Selectie")
            
            if st.session_state.sporza_team:
                team_df = df[df['Renner'].isin(st.session_state.sporza_team)].sort_values(by='Prijs', ascending=False)
                
                m1, m2, m3 = st.columns(3)
                tot_budget = team_df['Prijs'].sum()
                tot_ev = team_df['EV'].sum()
                
                m1.metric("Budget Over", f"€ {budget - tot_budget:.1f} M")
                m2.metric("Aantal Renners", f"{len(team_df)} / {aantal}")
                m3.metric("Verwachte Punten (EV)", f"{tot_ev:.0f}")
                
                ploeg_counts = team_df['Ploeg'].value_counts()
                if ploeg_counts.max() == max_ploeg:
                    st.warning(f"⚠️ Let op: Je zit aan je limiet ({max_ploeg}) bij: {', '.join(ploeg_counts[ploeg_counts == max_ploeg].index.tolist())}")
                
                display_cols = ['Renner', 'Ploeg', 'Prijs', 'EV']
                for col in df.columns:
                    if col not in display_cols and col not in ['Unnamed: 0', 'index']:
                        display_cols.append(col)
                        
                st.dataframe(team_df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.info("Klik op 'Bereken Sporza Team' om het algoritme te starten.")
                
    with tab2:
        st.header("📋 Alle Renners")
        
        c1, c2 = st.columns(2)
        with c1:
            search = st.text_input("Zoek Renner:")
        with c2:
            ploeg_filter = st.multiselect("Filter op Ploeg:", options=df['Ploeg'].unique())
            
        filtered_df = df.copy()
        if search:
            filtered_df = filtered_df[filtered_df['Renner'].str.contains(search, case=False, na=False)]
        if ploeg_filter:
            filtered_df = filtered_df[filtered_df['Ploeg'].isin(ploeg_filter)]
            
        st.dataframe(filtered_df.sort_values(by='EV', ascending=False), use_container_width=True, hide_index=True)

else:
    st.info("Upload eerst je Sporza dataset (.csv) in de zijbalk aan de linkerkant zodra je deze hebt om de solver te activeren.")
