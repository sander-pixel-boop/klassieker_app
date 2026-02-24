import streamlit as st
import pandas as pd
import pulp
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Scorito Klassiekers Solver 2026", layout="wide", page_icon="🚴‍♂️")

# --- DATA LADEN ---
@st.cache_data
def load_and_merge_data():
    try:
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', on_bad_lines='skip')
        df_prog.loc[df_prog['Prijs'] == 800000, 'Prijs'] = 750000
        
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        
        short_names = df_prog['Renner'].unique()
        full_names = df_stats['Renner'].unique()
        name_mapping = {}
        
        manual_overrides = {
            "Poel": "Mathieu van der Poel", "Aert": "Wout van Aert", "Lie": "Arnaud De Lie",
            "Gils": "Maxim Van Gils", "Berg": "Marijn van den Berg", "Broek": "Frank van den Broek"
        }
        
        for short in short_names:
            if short in manual_overrides:
                name_mapping[short] = manual_overrides[short]
            else:
                match_res = process.extractOne(short, full_names, scorer=fuzz.token_set_ratio)
                name_mapping[short] = match_res[0] if match_res else short

        df_prog['Renner_Full'] = df_prog['Renner'].map(name_mapping)
        
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 1500000), 'Renner_Full'] = 'Florian Vermeersch'
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Gianni Vermeersch'
        
        merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='inner')
        merged_df = merged_df.rename(columns={'Renner_Full': 'Renner'}).drop_duplicates(subset=['Renner', 'Prijs'])
        
        counts = {}
        unique_renners = []
        for r in merged_df['Renner']:
            if r in counts:
                counts[r] += 1
                unique_renners.append(f"{r} ({counts[r]})")
            else:
                counts[r] = 0
                unique_renners.append(r)
        merged_df['Renner'] = unique_renners
        
        race_cols = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'BDP', 'E3', 'GW', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
        available_races = [k for k in race_cols if k in merged_df.columns]
        
        for col in available_races + ['COB', 'HLL', 'SPR', 'AVG', 'Prijs']:
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0)
        
        merged_df['Total_Races'] = merged_df[available_races].sum(axis=1).astype(int)
        
        koers_stat_map = {'OHN':'COB','KBK':'SPR','SB':'HLL','PN':'HLL','TA':'SPR','MSR':'AVG','BDP':'SPR','E3':'COB','GW':'SPR','DDV':'COB','RVV':'COB','SP':'SPR','PR':'COB','BP':'HLL','AGR':'HLL','WP':'HLL','LBL':'HLL'}
        merged_df['Scorito_EV'] = 0.0
        for koers in available_races:
            stat = koers_stat_map.get(koers, 'AVG')
            merged_df['Scorito_EV'] += merged_df[koers] * ((merged_df[stat] / 100)**4 * 100)
        
        merged_df['Scorito_EV'] = merged_df['Scorito_EV'].fillna(0).round(0).astype(int)
        return merged_df, available_races, koers_stat_map
    except Exception as e:
        st.error(f"Fout in dataverwerking: {e}")
        return pd.DataFrame(), [], {}

df, race_cols, koers_mapping = load_and_merge_data()

if df.empty:
    st.warning("Data is leeg of kon niet worden geladen.")
    st.stop()

if "selected_riders" not in st.session_state:
    st.session_state.selected_riders = []

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
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=15))
    if pulp.LpStatus[prob.status] == 'Optimal':
        selected = [dataframe.loc[i, 'Renner'] for i in dataframe.index if rider_vars[i].varValue > 0.5]
        return selected[:max_riders]
    return None

# --- UI ---
st.title("🏆 Scorito Klassiekers 2026 AI Solver")
col_settings, col_selection = st.columns([1, 2], gap="large")

with col_settings:
    st.header("⚙️ Instellingen")
    max_ren = st.number_input("Totaal aantal renners", value=20)
    max_bud = st.number_input("Max Budget", value=45000000, step=500000)
    min_bud = st.number_input("Min Budget", value=43000000, step=500000)
    min_per_koers = st.slider("Min. renners per koers", 0, 15, 3)
    
    force_list = st.multiselect("🔒 Forceer:", options=df['Renner'].tolist())
    exclude_list = st.multiselect("❌ Sluit uit:", options=[r for r in df['Renner'].tolist() if r not in force_list])

    if st.button("🚀 Bereken Optimaal Team", type="primary", use_container_width=True):
        res = solve_knapsack(df, max_bud, min_bud, max_ren, min_per_koers, force_list, exclude_list, race_cols)
        if res:
            st.session_state.selected_riders = res
            st.rerun()
        else:
            st.error("Geen oplossing mogelijk. Probeer de eisen te versoepelen (bijv. lager min budget of minder renners per koers).")

with col_selection:
    st.header("1. Jouw Team")
    st.session_state.selected_riders = st.multiselect(
        "Selectie:", 
        options=df['Renner'].tolist(), 
        default=st.session_state.selected_riders
    )

# --- RESULTATEN ---
if st.session_state.selected_riders:
    current_df = df[df['Renner'].isin(st.session_state.selected_riders)].copy()
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Budget over", f"€ {max_bud - current_df['Prijs'].sum():,.0f}")
    m2.metric("Renners", f"{len(current_df)} / {max_ren}")
    m3.metric("Team EV", f"{current_df['Scorito_EV'].sum():.0f}")

    # 2. FINETUNER
    st.header("🔄 2. Finetuner")
    edit_df = current_df[['Renner', 'Prijs', 'Scorito_EV']].copy()
    edit_df.insert(0, 'Vervang', False)
    edited = st.data_editor(edit_df, hide_index=True, use_container_width=True, disabled=["Renner", "Prijs", "Scorito_EV"])
    
    if st.button("🔄 Vervang geselecteerde renners"):
        to_keep = edited[edited['Vervang'] == False]['Renner'].tolist()
        to_replace = edited[edited['Vervang'] == True]['Renner'].tolist()
        new_team = solve_knapsack(df, max_bud, min_bud, max_ren, min_per_koers, list(set(force_list + to_keep)), list(set(exclude_list + to_replace)), race_cols)
        if new_team:
            st.session_state.selected_riders = new_team
            st.rerun()

    # 3. MATRIX
    st.header("🗓️ 3. Startlijst Matrix")
    matrix = current_df[['Renner'] + race_cols].set_index('Renner')
    
    # Bereken de totalen per koers en voeg deze toe als eerste rij
    totals = matrix.sum().astype(int).astype(str)
    totals_row = pd.DataFrame([totals], index=['🏆 TOTAAL RENNERS'])
    
    # Verander enen en nullen in vinkjes en streepjes
    matrix = matrix.applymap(lambda x: '✅' if x == 1 else '-')
    
    # Koppel het totaal bovenaan
    display_matrix = pd.concat([totals_row, matrix])
    st.dataframe(display_matrix, use_container_width=True)

    # 4. KOPMAN
    st.header("🥇 4. Kopman Advies")
    kop_res = []
    for c in race_cols:
        starters = current_df[current_df[c] == 1]
        if not starters.empty:
            stat = koers_mapping.get(c, 'AVG')
            top = starters.sort_values(by=[stat, 'AVG'], ascending=False)['Renner'].tolist()
            kop_res.append({"Koers": c, "K1": top[0] if len(top)>0 else "-", "K2": top[1] if len(top)>1 else "-", "K3": top[2] if len(top)>2 else "-"})
    st.dataframe(pd.DataFrame(kop_res), hide_index=True, use_container_width=True)

    # 5. STATS
    st.header("📊 5. Team Statistieken")
    st.dataframe(current_df[['Renner', 'COB', 'HLL', 'SPR', 'AVG', 'Total_Races', 'Prijs', 'Scorito_EV']].sort_values(by='Scorito_EV', ascending=False), hide_index=True, use_container_width=True)
