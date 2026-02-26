import streamlit as st
import pandas as pd
import pulp
import json
import plotly.express as px
import plotly.graph_objects as go
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Scorito Klassiekers AI", layout="wide", page_icon="🏆")

# --- DATA LADEN (KLASSIEKERS SCORITO) ---
@st.cache_data
def load_and_merge_data():
    try:
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', on_bad_lines='skip')
        df_prog = df_prog.rename(columns={'RvB': 'BDP', 'IFF': 'GW'})
        
        if 'Prijs' not in df_prog.columns and df_prog['Renner'].astype(str).str.contains(r'\(.*\)', regex=True).any():
            extracted = df_prog['Renner'].str.extract(r'^(.*?)\s*\(([\d\.]+)[Mm]\)')
            df_prog['Renner'] = extracted[0].str.strip()
            df_prog['Prijs'] = pd.to_numeric(extracted[1], errors='coerce') * 1000000
            
        for col in df_prog.columns:
            if col not in ['Renner', 'Prijs']:
                df_prog[col] = df_prog[col].apply(lambda x: 1 if str(x).strip() in ['✓', 'v', 'V', '1', '1.0'] else 0)

        if 'Prijs' in df_prog.columns:
            df_prog['Prijs'] = df_prog['Prijs'].fillna(0)
            df_prog.loc[df_prog['Prijs'] == 800000, 'Prijs'] = 750000
        
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        
        if 'Team' not in df_stats.columns and 'Ploeg' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Ploeg': 'Team'})
            
        df_stats = df_stats.drop_duplicates(subset=['Renner'], keep='first')
        
        short_names = df_prog['Renner'].unique()
        full_names = df_stats['Renner'].unique()
        name_mapping = {}
        
        manual_overrides = {
            "Poel": "Mathieu van der Poel", "Aert": "Wout van Aert", "Lie": "Arnaud De Lie",
            "Gils": "Maxim Van Gils", "Broek": "Frank van den Broek",
            "Magnier": "Paul Magnier", "Pogacar": "Tadej Pogačar", "Skujins": "Toms Skujiņš",
            "Kooij": "Olav Kooij",
            "C. Hamilton": "Chris Hamilton", "L. Hamilton": "Lucas Hamilton",
            "H.M. Lopez": "Harold Martin Lopez", "J.P. Lopez": "Juan Pedro Lopez",
            "Ca. Rodriguez": "Carlos Rodriguez", "Cr. Rodriguez": "Cristian Rodriguez", "O. Rodriguez": "Oscar Rodriguez",
            "G. Serrano": "Gonzalo Serrano", "J. Serrano": "Javier Serrano",
            "A. Raccagni": "Andrea Raccagni", "G. Raccagni": "Gabriele Raccagni",
            "Mads Pedersen": "Mads Pedersen", "Rasmus Pedersen": "Rasmus Pedersen", 
            "Martin Pedersen": "Martin Pedersen", "S. Pedersen": "S. Pedersen",
            "Tim van Dijke": "Tim van Dijke", "Mick van Dijke": "Mick van Dijke",
            "Aurelien Paret-Peintre": "Aurélien Paret-Peintre", "Valentin Paret-Peintre": "Valentin Paret-Peintre",
            "Rui Oliveira": "Rui Oliveira", "Nelson Oliveira": "Nelson Oliveira", "Ivo Oliveira": "Ivo Oliveira",
            "Ivan Garcia Cortina": "Iván García Cortina", "Raul Garcia Pierna": "Raúl García Pierna",
            "Jonathan Milan": "Jonathan Milan", "Matteo Milan": "Matteo Milan",
            "Marijn van den Berg": "Marijn van den Berg", "Julius van den Berg": "Julius van den Berg"
        }
        
        for short in short_names:
            if short in manual_overrides:
                name_mapping[short] = manual_overrides[short]
            else:
                match_res = process.extractOne(short, full_names, scorer=fuzz.token_set_ratio)
                name_mapping[short] = match_res[0] if match_res and match_res[1] > 75 else short

        df_prog['Renner_Full'] = df_prog['Renner'].map(name_mapping)
        merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='left')
        
        if 'Renner_x' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Renner_x', 'Renner_y'], errors='ignore')
            
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
        
        early_races = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'BDP', 'E3', 'GW', 'DDV', 'RVV', 'SP', 'PR']
        late_races = ['BP', 'AGR', 'WP', 'LBL']
        
        available_early = [k for k in early_races if k in merged_df.columns]
        available_late = [k for k in late_races if k in merged_df.columns]
        available_races = available_early + available_late
        
        all_stats_cols = ['COB', 'HLL', 'SPR', 'AVG', 'FLT', 'MTN', 'ITT', 'GC', 'OR', 'TTL']
        for col in available_races + all_stats_cols + ['Prijs']:
            if col not in merged_df.columns:
                merged_df[col] = 0
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0).astype(int)
            
        if 'Team' not in merged_df.columns:
            merged_df['Team'] = 'Onbekend'
        else:
            merged_df['Team'] = merged_df['Team'].fillna('Onbekend')
        
        merged_df['Total_Races'] = merged_df[available_races].sum(axis=1).astype(int)
        
        koers_stat_map = {'OHN':'COB','KBK':'SPR','SB':'HLL','PN':'HLL','TA':'SPR','MSR':'AVG','BDP':'SPR','E3':'COB','GW':'SPR','DDV':'COB','RVV':'COB','SP':'SPR','PR':'COB','BP':'HLL','AGR':'HLL','WP':'HLL','LBL':'HLL'}
        
        return merged_df, available_early, available_late, koers_stat_map
    except Exception as e:
        st.error(f"Fout in dataverwerking: {e}")
        return pd.DataFrame(), [], [], {}

def calculate_ev(df, early_races, late_races, koers_stat_map, method):
    df = df.copy()
    df['EV_early'] = 0.0
    df['EV_late'] = 0.0
    
    scorito_pts = [100, 90, 80, 72, 64, 58, 52, 46, 40, 36, 32, 28, 24, 20, 16, 14, 12, 10, 8, 6]
    
    def get_race_ev(koers):
        stat = koers_stat_map.get(koers, 'AVG')
        starters = df[df[koers] == 1].copy()
        starters = starters.sort_values(by=[stat, 'AVG'], ascending=[False, False])
        
        race_ev = pd.Series(0.0, index=df.index)
        
        for i, idx in enumerate(starters.index):
            val = 0.0
            if "Scorito Ranking" in method:
                val = scorito_pts[i] if i < len(scorito_pts) else 0.0
            elif "Originele Curve" in method:
                val = (starters.loc[idx, stat] / 100)**4 * 100
            elif "Extreme Curve" in method:
                val = (starters.loc[idx, stat] / 100)**10 * 100
            elif "Tiers" in method:
                if i < 3: val = 80.0
                elif i < 8: val = 45.0
                elif i < 15: val = 20.0
                else: val = 0.0
                
            if i == 0: val *= 3.0
            elif i == 1: val *= 2.5
            elif i == 2: val *= 2.0
            
            race_ev.loc[idx] = val
        return race_ev

    for koers in early_races: df['EV_early'] += get_race_ev(koers)
    for koers in late_races: df['EV_late'] += get_race_ev(koers)
        
    df['EV_early'] = df['EV_early'].fillna(0).round(0).astype(int)
    df['EV_late'] = df['EV_late'].fillna(0).round(0).astype(int)
    df['Scorito_EV'] = df['EV_early'] + df['EV_late']
    df['Waarde (EV/M)'] = (df['Scorito_EV'] / (df['Prijs'] / 1000000)).replace([float('inf'), -float('inf')], 0).fillna(0).round(1)
    
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

# --- SOLVER ---
def solve_knapsack_with_transfers(dataframe, total_budget, min_budget, max_riders, min_per_race, force_early, ban_early, exclude_list, frozen_x, frozen_y, frozen_z, force_any, early_races, late_races, use_transfers):
    prob = pulp.LpProblem("Scorito_Solver", pulp.LpMaximize)
    
    if use_transfers:
        x = pulp.LpVariable.dicts("Base", dataframe.index, cat='Binary')
        y = pulp.LpVariable.dicts("Early", dataframe.index, cat='Binary')
        z = pulp.LpVariable.dicts("Late", dataframe.index, cat='Binary')
        
        prob += pulp.lpSum([x[i] * dataframe.loc[i, 'Scorito_EV'] + y[i] * dataframe.loc[i, 'EV_early'] + z[i] * dataframe.loc[i, 'EV_late'] for i in dataframe.index])
        
        for i in dataframe.index:
            renner = dataframe.loc[i, 'Renner']
            prob += x[i] + y[i] + z[i] <= 1
            if renner in force_early: prob += x[i] + y[i] == 1
            if renner in ban_early: prob += x[i] + y[i] == 0
            if renner in exclude_list: prob += x[i] + y[i] + z[i] == 0
            if renner in frozen_x: prob += x[i] == 1
            if renner in frozen_y: prob += y[i] == 1
            if renner in frozen_z: prob += z[i] == 1
            if renner in force_any: prob += x[i] + y[i] + z[i] == 1

        prob += pulp.lpSum([x[i] for i in dataframe.index]) == max_riders - 3
        prob += pulp.lpSum([y[i] for i in dataframe.index]) == 3
        prob += pulp.lpSum([z[i] for i in dataframe.index]) == 3
        
        prob += pulp.lpSum([(x[i] + y[i]) * dataframe.loc[i, 'Prijs'] for i in dataframe.index]) <= total_budget
        prob += pulp.lpSum([(x[i] + z[i]) * dataframe.loc[i, 'Prijs'] for i in dataframe.index]) <= total_budget
        prob += pulp.lpSum([(x[i] + y[i]) * dataframe.loc[i, 'Prijs'] for i in dataframe.index]) >= min_budget
        
        for koers in early_races: prob += pulp.lpSum([(x[i] + y[i]) * dataframe.loc[i, koers] for i in dataframe.index]) >= min_per_race
        for koers in late_races: prob += pulp.lpSum([(x[i] + z[i]) * dataframe.loc[i, koers] for i in dataframe.index]) >= min_per_race

        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=30))
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            base_team = [dataframe.loc[i, 'Renner'] for i in dataframe.index if x[i].varValue > 0.5]
            early_team = [dataframe.loc[i, 'Renner'] for i in dataframe.index if y[i].varValue > 0.5]
            late_team = [dataframe.loc[i, 'Renner'] for i in dataframe.index if z[i].varValue > 0.5]
            return base_team + early_team, {"uit": early_team, "in": late_team}
            
    else:
        rider_vars = pulp.LpVariable.dicts("Riders", dataframe.index, cat='Binary')
        prob += pulp.lpSum([dataframe.loc[i, 'Scorito_EV'] * rider_vars[i] for i in dataframe.index])
        prob += pulp.lpSum([rider_vars[i] for i in dataframe.index]) == max_riders
        prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) <= total_budget
        prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) >= min_budget
        for koers in early_races + late_races: prob += pulp.lpSum([dataframe.loc[i, koers] * rider_vars[i] for i in dataframe.index]) >= min_per_race
        for i in dataframe.index:
            renner = dataframe.loc[i, 'Renner']
            if renner in force_early: prob += rider_vars[i] == 1
            if renner in ban_early: prob += rider_vars[i] == 0
            if renner in exclude_list: prob += rider_vars[i] == 0
            if renner in frozen_x: prob += rider_vars[i] == 1
            if renner in force_any: prob += rider_vars[i] == 1
        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=15))
        if pulp.LpStatus[prob.status] == 'Optimal':
            selected = [dataframe.loc[i, 'Renner'] for i in dataframe.index if rider_vars[i].varValue > 0.5]
            return selected[:max_riders], None
            
    return None, None

# --- HOOFDCODE ---
df_raw, early_races, late_races, koers_mapping = load_and_merge_data()
if df_raw.empty:
    st.warning("Data is leeg of kon niet worden geladen.")
    st.stop()
    
race_cols = early_races + late_races

if "selected_riders" not in st.session_state: st.session_state.selected_riders = []
if "transfer_plan" not in st.session_state: st.session_state.transfer_plan = None
if "last_finetune" not in st.session_state: st.session_state.last_finetune = None

# --- SIDEBAR (CONTROLECENTRUM) ---
with st.sidebar:
    st.title("🏆 AI Coach")
    st.header("⚙️ Instellingen")
    use_transfers = st.checkbox("🔁 Bereken met 3 wissels (Parijs-Roubaix)", value=True)
    max_ren = st.number_input("Totaal aantal renners", value=20)
    max_bud = st.number_input("Max Budget", value=45000000, step=500000)
    min_bud = st.number_input("Min Budget", value=43000000, step=500000)
    min_per_koers = st.slider("Min. renners per koers", 0, 15, 3)
    
    st.divider()
    ev_method = st.selectbox(
        "🧮 Rekenmodel (EV)",
        ["1. Scorito Ranking (Dynamisch)", "2. Originele Curve (Macht 4)", "3. Extreme Curve (Macht 10)", "4. Tiers & Spreiding (Realistisch)"]
    )
    df = calculate_ev(df_raw, early_races, late_races, koers_mapping, ev_method)
    
    st.divider()
    with st.expander("🔒 Renners Forceren / Uitsluiten", expanded=False):
        force_early = st.multiselect("🟢 Moet in team:", options=df['Renner'].tolist())
        ban_early = st.multiselect("🔴 Niet als basis (evt wissel):", options=[r for r in df['Renner'].tolist() if r not in force_early])
        exclude_list = st.multiselect("🚫 Compleet negeren:", options=[r for r in df['Renner'].tolist() if r not in force_early + ban_early])

    st.divider()
    if st.button("🚀 BEREKEN OPTIMAAL TEAM", type="primary", use_container_width=True):
        st.session_state.last_finetune = None
        res, transfer_plan = solve_knapsack_with_transfers(
            df, max_bud, min_bud, max_ren, min_per_koers, force_early, ban_early, exclude_list, [], [], [], [], early_races, late_races, use_transfers
        )
        if res:
            st.session_state.selected_riders = res
            st.session_state.transfer_plan = transfer_plan
            st.rerun()
        else:
            st.error("Geen oplossing mogelijk met deze eisen.")

st.title("🏆 Voorjaarsklassiekers: Scorito")
tab1, tab2, tab3 = st.tabs(["🚀 Jouw Team & Analyse", "📋 Alle Renners (Database)", "ℹ️ Uitleg"])

with tab1:
    if st.session_state.selected_riders:
        all_display_riders = st.session_state.selected_riders + (st.session_state.transfer_plan['in'] if st.session_state.transfer_plan else [])
        current_df = df[df['Renner'].isin(all_display_riders)].copy()
        
        def bepaal_rol(naam):
            if st.session_state.transfer_plan:
                if naam in st.session_state.transfer_plan['uit']: return 'Verkopen na PR'
                if naam in st.session_state.transfer_plan['in']: return 'Kopen na PR'
            return 'Basis'
            
        current_df['Rol'] = current_df['Renner'].apply(bepaal_rol)
        current_df['Type'] = current_df.apply(bepaal_klassieker_type, axis=1)
        start_team_df = current_df[current_df['Rol'] != 'Kopen na PR']

        # --- TOP LEVEL METRICS ---
        st.subheader("📊 Dashboard")
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Budget over (Start)", f"€ {max_bud - start_team_df['Prijs'].sum():,.0f}")
        m2.metric("🚴 Renners (Start)", f"{len(start_team_df)} / {max_ren}")
        
        if st.session_state.transfer_plan:
            total_ev = start_team_df['EV_early'].sum() + current_df[current_df['Rol'] == 'Kopen na PR']['EV_late'].sum() + current_df[current_df['Rol'] == 'Basis']['EV_late'].sum()
            m3.metric("🎯 Team EV (Incl. wissels)", f"{total_ev:.0f}")
        else:
            m3.metric("🎯 Team EV", f"{start_team_df['Scorito_EV'].sum():.0f}")
            
        st.divider()

        # --- JOUW TEAM ---
        col_t1, col_t2 = st.columns([1, 1], gap="large")
        with col_t1:
            st.markdown("**🛡️ Jouw Basis-Team**")
            st.session_state.selected_riders = st.multiselect("Selectie (Start):", options=df['Renner'].tolist(), default=st.session_state.selected_riders, label_visibility="collapsed")
        
        with col_t2:
            if st.session_state.transfer_plan:
                st.markdown("**🔁 Wissel-Strategie na Parijs-Roubaix**")
                c_uit, c_in = st.columns(2)
                with c_uit: st.error("❌ **Verkopen:**\n" + "\n".join([f"- {r}" for r in st.session_state.transfer_plan['uit']]))
                with c_in: st.success("📥 **Inkopen:**\n" + "\n".join([f"- {r}" for r in st.session_state.transfer_plan['in']]))

        # --- KWALITEITSCONTROLE ---
        matrix_df_check = current_df[['Renner', 'Rol', 'Type', 'Prijs'] + race_cols].set_index('Renner')
        active_matrix_check = matrix_df_check.copy()
        if st.session_state.transfer_plan:
            for r in early_races: active_matrix_check.loc[active_matrix_check['Rol'] == 'Kopen na PR', r] = 0
            for r in late_races: active_matrix_check.loc[active_matrix_check['Rol'] == 'Verkopen na PR', r] = 0

        warnings = []
        for c in race_cols:
            starters = active_matrix_check[active_matrix_check[c] == 1]
            if len(starters) > 0:
                stat = koers_mapping.get(c, 'AVG')
                max_stat = current_df[current_df['Renner'].isin(starters.index)][stat].max()
                if max_stat < 85:
                    warnings.append(f"**{c}**: Beste kopman scoort slechts {max_stat} op de benodigde '{stat}'-statistiek. Dit is een zwakke plek.")
            else:
                warnings.append(f"**{c}**: GEEN actieve renners aan de start!")

        if warnings:
            with st.expander("🚨 **Kwaliteitscontrole: Gevonden zwaktes in je programma**", expanded=True):
                for w in warnings: st.warning(w)
        
        st.divider()

        # --- FINETUNER (CONTAINER) ---
        with st.container(border=True):
            st.subheader("🛠️ Team Finetuner")
            st.markdown("Gooi een renner eruit en laat de AI een vervanger zoeken, of forceer rollen.")
            
            if st.session_state.last_finetune:
                st.success(f"✅ **Wijziging doorgevoerd!** ❌ Eruit: {', '.join(st.session_state.last_finetune['uit'])} | 📥 Erin: {', '.join(st.session_state.last_finetune['in'])}")
                st.session_state.last_finetune = None 
            
            c_fine1, c_fine2 = st.columns(2)
            with c_fine1: to_replace = st.multiselect("❌ Selecteer renner(s) om te verwijderen:", options=all_display_riders)
            with c_fine2: 
                available_replacements = [r for r in df['Renner'].tolist() if r not in all_display_riders]
                to_add_manual = st.multiselect("📥 Handmatige vervanger(s) (Optioneel):", options=available_replacements)
                
            to_add = to_add_manual.copy()
                
            if to_replace:
                freed_budget = df[df['Renner'].isin(to_replace)]['Prijs'].sum()
                max_affordable = freed_budget + (max_bud - start_team_df['Prijs'].sum())
                sugg_df = df[~df['Renner'].isin(all_display_riders)][df['Prijs'] <= max_affordable].sort_values(by='Scorito_EV', ascending=False).head(5)
                
                if not sugg_df.empty:
                    st.info(f"💡 **Top Suggesties (Budget per renner: € {max_affordable:,.0f}):**")
                    st.dataframe(sugg_df[['Renner', 'Prijs', 'Waarde (EV/M)', 'Scorito_EV', 'Type']], hide_index=True, use_container_width=True)
                    sugg_keuze = st.multiselect("👉 Of selecteer hier directe suggesties:", options=sugg_df['Renner'].tolist())
                    to_add = list(set(to_add + sugg_keuze))
                    
            with st.expander("⚙️ Geavanceerd: Rol forceren"):
                c_r1, c_r2, c_r3 = st.columns(3)
                with c_r1: force_new_base = st.multiselect("🛡️ Forceer BASIS", options=list(set(all_display_riders + to_add)))
                with c_r2: force_new_uit = st.multiselect("❌ Forceer VERKOPEN na PR", options=[r for r in list(set(all_display_riders + to_add)) if r not in force_new_base])
                with c_r3: force_new_in = st.multiselect("📥 Forceer INKOPEN na PR", options=[r for r in list(set(all_display_riders + to_add)) if r not in force_new_base + force_new_uit])
                is_forcing_roles = bool(force_new_base or force_new_uit or force_new_in)
                freeze_others = st.checkbox("🔒 Bevries de rollen van overige renners", value=not is_forcing_roles)

            if to_replace or to_add or is_forcing_roles:
                if st.button("🚀 VOER WIJZIGING DOOR", type="primary", use_container_width=True):
                    old_team = set(all_display_riders)
                    to_keep = [r for r in all_display_riders if r not in to_replace]
                    frozen_x, frozen_y, frozen_z, force_any = [], [], [], []
                    
                    for r in list(set(to_keep + to_add)):
                        if r in force_new_base: frozen_x.append(r)
                        elif r in force_new_uit: frozen_y.append(r)
                        elif r in force_new_in: frozen_z.append(r)
                        else:
                            if freeze_others and r in current_df['Renner'].values:
                                rol = current_df[current_df['Renner'] == r]['Rol'].values[0]
                                if rol == 'Basis': frozen_x.append(r)
                                elif rol == 'Verkopen na PR': frozen_y.append(r)
                                elif rol == 'Kopen na PR': frozen_z.append(r)
                            else: force_any.append(r)
                    
                    new_res, new_plan = solve_knapsack_with_transfers(
                        df, max_bud, min_bud, max_ren, min_per_koers, force_early, ban_early, list(set(exclude_list + to_replace)), frozen_x, frozen_y, frozen_z, force_any, early_races, late_races, use_transfers
                    )
                    if new_res:
                        new_team = set(new_res)
                        if new_plan: new_team.update(new_plan['in'])
                        st.session_state.last_finetune = {"uit": list(old_team - new_team), "in": list(new_team - old_team)}
                        st.session_state.selected_riders = new_res
                        st.session_state.transfer_plan = new_plan
                        st.rerun()
                    else:
                        st.error("Geen oplossing mogelijk! Probeer 'Bevries rollen' uit te vinken of versoepel de budget-eisen.")

        # --- GRAFIEKEN ---
        st.header("📈 Visuele Analyse")
        c_chart1, c_chart2 = st.columns(2)
        c_chart3, c_chart4 = st.columns(2)
        
        with c_chart1:
            start_stats = start_team_df[['COB', 'HLL', 'SPR', 'AVG']].mean().round(1)
            fig_radar = go.Figure(go.Scatterpolar(r=[start_stats['COB'], start_stats['HLL'], start_stats['SPR'], start_stats['AVG']] + [start_stats['COB']], theta=['Kassei', 'Heuvel', 'Sprint', 'Allround', 'Kassei'], fill='toself'))
            fig_radar.update_layout(height=320, polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, title="Skill Profiel (Start-Team)", margin=dict(t=40, b=20, l=40, r=40))
            st.plotly_chart(fig_radar, use_container_width=True)
            
        with c_chart2:
            fig_donut = px.pie(current_df.groupby('Rol')['Prijs'].sum().reset_index(), values='Prijs', names='Rol', hole=0.4, title="Budget Verdeling")
            fig_donut.update_layout(height=320, margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_donut, use_container_width=True)
            
        with c_chart3:
            t_data = current_df.groupby('Type').agg(Prijs=('Prijs', 'sum'), Aantal=('Renner', 'count')).reset_index()
            t_data['Label'] = t_data['Type'] + ' (' + t_data['Aantal'].astype(str) + ')'
            fig_type = px.pie(t_data, values='Prijs', names='Label', hole=0.4, title="Renners per Type")
            fig_type.update_layout(height=320, margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_type, use_container_width=True)
            
        with c_chart4:
            fig_teams = px.bar(current_df['Team'].value_counts().reset_index().rename(columns={'count':'Aantal'}), x='Team', y='Aantal', title="Teampunten Spreiding", text_auto=True)
            fig_teams.update_layout(height=320, xaxis_title="", yaxis_title="Renners", margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_teams, use_container_width=True)

        # --- DATA TABELLEN ---
        st.header("🗓️ Kalender & Statistieken")
        
        tab_matrix, tab_stats, tab_kopman = st.tabs(["Startlijst Matrix", "Team Statistieken", "Kopmannen Advies"])
        
        def color_rows(row):
            if row.name == '🏆 TOTAAL AAN DE START': return ['background-color: rgba(255, 215, 0, 0.2); font-weight: bold; border-top: 2px solid black'] * len(row)
            if row['Rol'] == 'Verkopen na PR': return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row)
            if row['Rol'] == 'Kopen na PR': return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row)
            return [''] * len(row)

        with tab_matrix:
            matrix_df = current_df[['Renner', 'Rol', 'Type', 'Team', 'Prijs'] + race_cols].set_index('Renner')
            active_matrix = matrix_df.copy()
            if st.session_state.transfer_plan:
                for r in early_races: active_matrix.loc[active_matrix['Rol'] == 'Kopen na PR', r] = 0
                for r in late_races: active_matrix.loc[active_matrix['Rol'] == 'Verkopen na PR', r] = 0

            display_matrix = matrix_df[race_cols].applymap(lambda x: '✅' if x == 1 else '-')
            display_matrix.insert(0, 'Rol', matrix_df['Rol'])
            display_matrix.insert(1, 'Type', matrix_df['Type'])
            display_matrix.insert(2, 'Prijs', matrix_df['Prijs'].apply(lambda x: f"€ {x/1000000:.2f}M"))
            display_matrix.insert(3, 'Koersen', active_matrix[race_cols].sum(axis=1).astype(int))
            
            if 'PR' in display_matrix.columns: display_matrix.insert(display_matrix.columns.get_loc('PR') + 1, '🔁', '|')
                
            totals_dict = {c: str(int(active_matrix[c].sum())) if c in race_cols else ('|' if c == '🔁' else ('TOTAAL ACTIEF' if c == 'Rol' else '')) for c in display_matrix.columns}
            display_matrix.loc['🏆 TOTAAL AAN DE START'] = pd.Series(totals_dict)
            st.dataframe(display_matrix.style.apply(color_rows, axis=1), use_container_width=True)

        with tab_stats:
            stats_overzicht = current_df[['Renner', 'Rol', 'Type', 'Team', 'Prijs', 'Waarde (EV/M)', 'Scorito_EV']].copy()
            stats_overzicht['Prijs'] = stats_overzicht['Prijs'].apply(lambda x: f"€ {x/1000000:.2f}M")
            st.dataframe(stats_overzicht.sort_values(by=['Rol', 'Scorito_EV'], ascending=[True, False]).style.apply(lambda r: ['background-color: rgba(255, 99, 71, 0.2)']*len(r) if r['Rol'] == 'Verkopen na PR' else (['background-color: rgba(144, 238, 144, 0.2)']*len(r) if r['Rol'] == 'Kopen na PR' else ['']*len(r)), axis=1), hide_index=True, use_container_width=True)

        with tab_kopman:
            kop_res = []
            for c in race_cols:
                starters = active_matrix[active_matrix[c] == 1]
                if not starters.empty:
                    stat = koers_mapping.get(c, 'AVG')
                    top = current_df[current_df['Renner'].isin(starters.index)].sort_values(by=[stat, 'AVG'], ascending=False)['Renner'].tolist()
                    kop_res.append({"Koers": c, "🥇 Kopman 1": top[0] if len(top)>0 else "-", "🥈 Kopman 2": top[1] if len(top)>1 else "-", "🥉 Kopman 3": top[2] if len(top)>2 else "-"})
            st.dataframe(pd.DataFrame(kop_res), hide_index=True, use_container_width=True)
            
        st.divider()
        with st.expander("💾 Team Opslaan / Exporteren"):
            if st.session_state.selected_riders:
                save_data = {"selected_riders": st.session_state.selected_riders, "transfer_plan": st.session_state.transfer_plan}
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1: st.download_button("📥 Download als .JSON (Voor later inladen)", data=json.dumps(save_data), file_name="scorito_team.json", mime="application/json", use_container_width=True)
                with c_dl2: st.download_button("📊 Download als .CSV (Voor Excel)", data=current_df[['Renner', 'Prijs', 'Team', 'Waarde (EV/M)', 'Scorito_EV']].to_csv(index=False), file_name="scorito_team.csv", mime="text/csv", use_container_width=True)
            uploaded_file = st.file_uploader("📂 Upload een .json bestand om een team te laden:", type="json")
            if uploaded_file and st.button("Laad Team in", use_container_width=True):
                try:
                    ld = json.load(uploaded_file)
                    st.session_state.selected_riders = [process.extractOne(r, df['Renner'].tolist(), scorer=fuzz.token_set_ratio)[0] for r in ld.get("selected_riders", [])]
                    st.session_state.transfer_plan = {"uit": [process.extractOne(r, df['Renner'].tolist(), scorer=fuzz.token_set_ratio)[0] for r in ld.get("transfer_plan", {}).get("uit", [])], "in": [process.extractOne(r, df['Renner'].tolist(), scorer=fuzz.token_set_ratio)[0] for r in ld.get("transfer_plan", {}).get("in", [])]} if ld.get("transfer_plan") else None
                    st.rerun()
                except: st.error("Fout bij inladen.")
    else:
        st.info("Kies je instellingen in de linker zijbalk en klik op **Bereken Optimaal Team** om te starten!")

with tab2:
    st.header("📋 Database: Alle Renners")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: search_name = st.text_input("🔍 Zoek op naam of Ploeg:")
    with col_f2: price_filter = st.slider("💰 Prijs range", int(df['Prijs'].min()), int(df['Prijs'].max()), (int(df['Prijs'].min()), int(df['Prijs'].max())), 250000)
    with col_f3: race_filter = st.multiselect("🏁 Rijdt geselecteerde koersen:", options=race_cols)

    f_df = df.copy()
    f_df['Type'] = f_df.apply(bepaal_klassieker_type, axis=1)
    if search_name: f_df = f_df[f_df['Renner'].str.contains(search_name, case=False, na=False) | f_df['Team'].str.contains(search_name, case=False, na=False)]
    f_df = f_df[(f_df['Prijs'] >= price_filter[0]) & (f_df['Prijs'] <= price_filter[1])]
    if race_filter: f_df = f_df[f_df[race_filter].sum(axis=1) == len(race_filter)]

    d_df = f_df[['Renner', 'Team', 'Prijs', 'Waarde (EV/M)', 'Type', 'Total_Races', 'Scorito_EV'] + race_cols].copy().rename(columns={'Total_Races': 'Koersen'})
    d_df['Prijs'] = d_df['Prijs'].apply(lambda x: f"€ {x/1000000:.2f}M")
    d_df[race_cols] = d_df[race_cols].applymap(lambda x: '✅' if x == 1 else '-')
    if 'PR' in d_df.columns: d_df.insert(d_df.columns.get_loc('PR') + 1, '🔁', '|')
    st.dataframe(d_df.sort_values(by='Scorito_EV', ascending=False), use_container_width=True, hide_index=True)

with tab3:
    st.header("ℹ️ Hoe werkt deze Solver?")
    st.markdown("""
    Deze applicatie berekent wiskundig het meest optimale Scorito-team voor het Voorjaarsklassiekers-spel.
    
    ### 1. Rekenmodellen (EV Berekening)
    * **Scorito Ranking (Dynamisch):** Deelt exacte Scorito-punten uit o.b.v. positie in startlijst.
    * **Originele Curve (Macht 4):** Vloeiende exponentiële lijn (`(Stat / 100)⁴ × 100`).
    * **Extreme Curve (Macht 10):** Straft opvullers af, alleen wereldtop behoudt punten.
    * **Tiers & Spreiding:** Meest realistisch; verdeelt verwachte punten over subgroepen (Tiers) om chaos en valpartijen te simuleren.
    
    ### 2. Het Algoritme (Knapsack Problem)
    Pulp (een wiskundige library) berekent miljoenen combinaties om binnen je budget de 20 (of 23) renners te vinden die de maximale team-waarde opleveren.
    """)
