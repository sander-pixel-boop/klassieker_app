import streamlit as st
import pandas as pd
import pulp
import json
import plotly.express as px
import plotly.graph_objects as go
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Scorito Klassiekers", layout="wide", page_icon="🏆")

# --- DATA LADEN (KLASSIEKERS SCORITO) ---
@st.cache_data
def load_and_merge_data():
    try:
        # Bron: Gebruiker / Kopmanpuzzel ruwe copy-paste data
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', on_bad_lines='skip')
        
        # Hernoem afwijkende afkortingen naar de app-standaard
        df_prog = df_prog.rename(columns={'RvB': 'BDP', 'IFF': 'GW'})
        
        # Haal de prijs uit de naam ("Pogacar (7.00M)" -> "Pogacar" en 7000000)
        if 'Prijs' not in df_prog.columns and df_prog['Renner'].astype(str).str.contains(r'\(.*\)', regex=True).any():
            extracted = df_prog['Renner'].str.extract(r'^(.*?)\s*\(([\d\.]+)[Mm]\)')
            df_prog['Renner'] = extracted[0].str.strip()
            df_prog['Prijs'] = pd.to_numeric(extracted[1], errors='coerce') * 1000000
            
        # Vinkjes omzetten naar 1, leeg naar 0
        for col in df_prog.columns:
            if col not in ['Renner', 'Prijs']:
                df_prog[col] = df_prog[col].apply(lambda x: 1 if str(x).strip() in ['✓', 'v', 'V', '1', '1.0'] else 0)

        # Toepassen regel: 0.8M -> 750000
        if 'Prijs' in df_prog.columns:
            df_prog['Prijs'] = df_prog['Prijs'].fillna(0)
            df_prog.loc[df_prog['Prijs'] == 800000, 'Prijs'] = 750000
        
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        
        # Zorg dat de Team kolom correct heet
        if 'Team' not in df_stats.columns and 'Ploeg' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Ploeg': 'Team'})
            
        df_stats = df_stats.drop_duplicates(subset=['Renner'], keep='first')
        
        short_names = df_prog['Renner'].unique()
        full_names = df_stats['Renner'].unique()
        name_mapping = {}
        
        # Voorkom dat de Fuzzy Matcher broers en naamgenoten samenvoegt
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
        
        # Voeg nu ook alle andere stats van Wielerorakel toe
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
                
            # Kopman Bonus toepassen
            if i == 0: val *= 3.0
            elif i == 1: val *= 2.5
            elif i == 2: val *= 2.0
            
            race_ev.loc[idx] = val
            
        return race_ev

    for koers in early_races:
        df['EV_early'] += get_race_ev(koers)
        
    for koers in late_races:
        df['EV_late'] += get_race_ev(koers)
        
    df['EV_early'] = df['EV_early'].fillna(0).round(0).astype(int)
    df['EV_late'] = df['EV_late'].fillna(0).round(0).astype(int)
    df['Scorito_EV'] = df['EV_early'] + df['EV_late']
    
    # Value for Money (EV per Miljoen)
    df['Waarde (EV/M)'] = (df['Scorito_EV'] / (df['Prijs'] / 1000000)).replace([float('inf'), -float('inf')], 0).fillna(0).round(1)
    
    return df

# Geavanceerde Type Bepaling (Pakt dubbele combinaties bij elitescores)
def bepaal_klassieker_type(row):
    cob = row.get('COB', 0)
    hll = row.get('HLL', 0)
    spr = row.get('SPR', 0)
    
    elite = []
    if cob >= 85: elite.append('Kassei')
    if hll >= 85: elite.append('Heuvel')
    if spr >= 85: elite.append('Sprint')
    
    if len(elite) == 3:
        return 'Allround / Multispecialist'
    elif len(elite) == 2:
        return ' / '.join(elite)
    elif len(elite) == 1:
        return elite[0]
    else:
        s = {
            'Kassei': cob, 
            'Heuvel': hll, 
            'Sprint': spr, 
            'Klimmer': row.get('MTN', 0),
            'Tijdrit': row.get('ITT', 0),
            'Klassement': row.get('GC', 0)
        }
        if sum(s.values()) == 0:
            return 'Onbekend'
        return max(s, key=s.get)

# --- SOLVER SCORITO ---
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
        
        for koers in early_races:
            prob += pulp.lpSum([(x[i] + y[i]) * dataframe.loc[i, koers] for i in dataframe.index]) >= min_per_race
        for koers in late_races:
            prob += pulp.lpSum([(x[i] + z[i]) * dataframe.loc[i, koers] for i in dataframe.index]) >= min_per_race

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
        
        for koers in early_races + late_races:
            prob += pulp.lpSum([dataframe.loc[i, koers] * rider_vars[i] for i in dataframe.index]) >= min_per_race
        
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

# --- SIDEBAR: EV METHODE ---
st.sidebar.header("🧮 Rekenmodel")
ev_method = st.sidebar.selectbox(
    "EV Berekeningsmethode",
    [
        "1. Scorito Ranking (Dynamisch)", 
        "2. Originele Curve (Macht 4)",
        "3. Extreme Curve (Macht 10)", 
        "4. Tiers & Spreiding (Realistisch)"
    ],
    help="Kies hoe het algoritme de verwachte punten (EV) per renner berekent. Dit beïnvloedt direct welke renners de AI selecteert."
)

# Bereken de EV dynamisch op basis van de geselecteerde methode
df = calculate_ev(df_raw, early_races, late_races, koers_mapping, ev_method)

if "selected_riders" not in st.session_state:
    st.session_state.selected_riders = []
if "transfer_plan" not in st.session_state:
    st.session_state.transfer_plan = None
if "last_finetune" not in st.session_state:
    st.session_state.last_finetune = None

st.title("🏆 Voorjaarsklassiekers: Scorito")

tab1, tab2, tab3 = st.tabs(["🚀 Team Builder", "📋 Alle Renners", "ℹ️ Uitleg & Credits"])

with tab1:
    col_settings, col_selection = st.columns([1, 2], gap="large")

    with col_settings:
        st.header("⚙️ Instellingen")
        use_transfers = st.checkbox("🔁 Bereken met 3 wissels na Parijs-Roubaix", value=True)
        max_ren = st.number_input("Totaal aantal renners (Start)", value=20)
        max_bud = st.number_input("Max Budget", value=45000000, step=500000)
        min_bud = st.number_input("Min Budget", value=43000000, step=500000)
        min_per_koers = st.slider("Min. renners per koers", 0, 15, 3)
        
        st.divider()
        st.write("**Renners Forceren / Uitsluiten**")
        
        force_early = st.multiselect("🟢 Moet in start-team (Rol wordt bepaald door AI):", options=df['Renner'].tolist())
        ban_early = st.multiselect("🔴 Mag NIET in start-team (Misschien wel als wissel):", options=[r for r in df['Renner'].tolist() if r not in force_early])
        exclude_list = st.multiselect("🚫 Compleet negeren (Hele spel uitsluiten):", options=[r for r in df['Renner'].tolist() if r not in force_early + ban_early])

        if st.button("🚀 Bereken Optimaal Team", type="primary", use_container_width=True):
            st.session_state.last_finetune = None
            res, transfer_plan = solve_knapsack_with_transfers(
                df, max_bud, min_bud, max_ren, min_per_koers, 
                force_early, ban_early, exclude_list, 
                [], [], [], [], 
                early_races, late_races, use_transfers
            )
            if res:
                st.session_state.selected_riders = res
                st.session_state.transfer_plan = transfer_plan
                st.rerun()
            else:
                st.error("Geen oplossing mogelijk. Probeer de eisen te versoepelen (bijv. minder dure renners tegelijk forceren of budget te verhogen).")
                
        # --- OPSLAAN / LADEN BLOK ---
        st.divider()
        with st.expander("💾 Team Opslaan / Exporteren"):
            if st.session_state.selected_riders:
                save_data = {
                    "selected_riders": st.session_state.selected_riders,
                    "transfer_plan": st.session_state.transfer_plan
                }
                json_str = json.dumps(save_data)
                
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                    st.download_button(
                        label="📥 Download als .JSON (Backup)",
                        data=json_str,
                        file_name="scorito_team.json",
                        mime="application/json",
                        use_container_width=True
                    )
                with c_dl2:
                    current_df_export = df[df['Renner'].isin(st.session_state.selected_riders + (st.session_state.transfer_plan['in'] if st.session_state.transfer_plan else []))].copy()
                    csv_export = current_df_export[['Renner', 'Prijs', 'Team', 'Waarde (EV/M)', 'Scorito_EV']].to_csv(index=False)
                    st.download_button(
                        label="📊 Download als .CSV (Excel)",
                        data=csv_export,
                        file_name="scorito_team.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            uploaded_file = st.file_uploader("📂 Upload een bewaard team (.json)", type="json")
            if uploaded_file is not None:
                if st.button("Laad Team in", use_container_width=True):
                    try:
                        loaded_data = json.load(uploaded_file)
                        oude_selectie = loaded_data.get("selected_riders", [])
                        oud_plan = loaded_data.get("transfer_plan", None)
                        
                        huidige_renners = df['Renner'].tolist()
                        
                        def update_naam(naam):
                            if naam in huidige_renners: return naam
                            match = process.extractOne(naam, huidige_renners, scorer=fuzz.token_set_ratio)
                            return match[0] if match and match[1] > 80 else naam

                        st.session_state.selected_riders = [update_naam(r) for r in oude_selectie]
                        
                        if oud_plan:
                            st.session_state.transfer_plan = {
                                "uit": [update_naam(r) for r in oud_plan.get("uit", [])],
                                "in": [update_naam(r) for r in oud_plan.get("in", [])]
                            }
                        else:
                            st.session_state.transfer_plan = None
                            
                        st.session_state.last_finetune = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fout bij inladen: {e}")

    with col_selection:
        st.header("1. Jouw Start-Team (voor de wissels)")
        st.session_state.selected_riders = st.multiselect(
            "Selectie:", 
            options=df['Renner'].tolist(), 
            default=st.session_state.selected_riders
        )
        
        if st.session_state.transfer_plan:
            st.success("✅ **Wissel-Strategie na Parijs-Roubaix:**")
            c_uit, c_in = st.columns(2)
            with c_uit:
                st.error(f"❌ **Verkopen (3):**\n" + "\n".join([f"- {r}" for r in st.session_state.transfer_plan['uit']]))
            with c_in:
                st.info(f"📥 **Inkopen (3):**\n" + "\n".join([f"- {r}" for r in st.session_state.transfer_plan['in']]))

    # --- RESULTATEN & GRAFIEKEN ---
    if st.session_state.selected_riders:
        if st.session_state.transfer_plan:
            all_display_riders = st.session_state.selected_riders + st.session_state.transfer_plan['in']
        else:
            all_display_riders = st.session_state.selected_riders

        current_df = df[df['Renner'].isin(all_display_riders)].copy()
        
        def bepaal_rol(naam):
            if st.session_state.transfer_plan:
                if naam in st.session_state.transfer_plan['uit']: return 'Verkopen na PR'
                if naam in st.session_state.transfer_plan['in']: return 'Kopen na PR'
            return 'Basis'
            
        current_df['Rol'] = current_df['Renner'].apply(bepaal_rol)
        current_df['Type'] = current_df.apply(bepaal_klassieker_type, axis=1)

        start_team_df = current_df[current_df['Rol'] != 'Kopen na PR']
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Budget over (Start)", f"€ {max_bud - start_team_df['Prijs'].sum():,.0f}")
        m2.metric("Renners (Start)", f"{len(start_team_df)} / {max_ren}")
        
        if st.session_state.transfer_plan:
            ev_start = start_team_df['EV_early'].sum()
            in_riders_ev = current_df[current_df['Rol'] == 'Kopen na PR']['EV_late'].sum()
            base_riders_late_ev = current_df[current_df['Rol'] == 'Basis']['EV_late'].sum()
            m3.metric("Team EV (Incl. wissels)", f"{ev_start + base_riders_late_ev + in_riders_ev:.0f}")
        else:
            m3.metric("Team EV", f"{start_team_df['Scorito_EV'].sum():.0f}")

        # --- KWALITEITSCONTROLE WAARSCHUWINGEN ---
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
                starters_stats = current_df[current_df['Renner'].isin(starters.index)]
                max_stat = starters_stats[stat].max()
                if max_stat < 85:
                    warnings.append(f"**{c}**: Je beste renner heeft slechts een '{stat}'-score van {max_stat}. Overweeg een sterkere kopman voor deze koers!")
            else:
                warnings.append(f"**{c}**: Je hebt momenteel GEEN actieve renners aan de start staan!")

        if warnings:
            with st.expander("🚨 **Kwaliteitscontrole: Gevonden zwaktes in je programma**", expanded=True):
                for w in warnings:
                    st.warning(w)
        else:
            st.success("✅ **Kwaliteitscontrole:** Je team ziet er robuust uit met een sterke kopman (>85 score) voor élke koers!")

        # --- GRAFIEKEN ---
        st.header("📈 Team Analyse")
        
        c_chart1, c_chart2 = st.columns(2)
        c_chart3, c_chart4 = st.columns(2)
        
        with c_chart1:
            start_stats = start_team_df[['COB', 'HLL', 'SPR', 'AVG']].mean().round(1)
            categories = ['Kassei (COB)', 'Heuvel (HLL)', 'Sprint (SPR)', 'Allround (AVG)']
            values = [start_stats['COB'], start_stats['HLL'], start_stats['SPR'], start_stats['AVG']]
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                name='Gemiddelde'
            ))
            fig_radar.update_layout(
                height=350,
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                title="Gemiddelde Stats (Start-Team)",
                margin=dict(t=40, b=20, l=40, r=40)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
        with c_chart2:
            budget_data = current_df.groupby('Rol')['Prijs'].sum().reset_index()
            fig_donut = px.pie(budget_data, values='Prijs', names='Rol', hole=0.4, title="Budget per Rol")
            fig_donut.update_layout(height=350, margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_donut, use_container_width=True)
            
        with c_chart3:
            type_data = current_df.groupby('Type').agg(
                Prijs=('Prijs', 'sum'),
                Aantal=('Renner', 'count')
            ).reset_index()
            type_data['Label'] = type_data['Type'] + ' (' + type_data['Aantal'].astype(str) + ')'
            fig_type = px.pie(type_data, values='Prijs', names='Label', hole=0.4, title="Budget & Aantal per Renner Type")
            fig_type.update_layout(height=350, margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_type, use_container_width=True)
            
        with c_chart4:
            team_data = current_df['Team'].value_counts().reset_index()
            team_data.columns = ['Team', 'Aantal']
            fig_teams = px.bar(team_data, x='Team', y='Aantal', title="Spreiding per Ploeg (Teampunten)", text_auto=True)
            fig_teams.update_layout(height=350, xaxis_title="", yaxis_title="Aantal Renners", margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_teams, use_container_width=True)

        # --- FINETUNER BLOK ---
        st.divider()
        st.header("🔄 2. Team Finetunen")
        st.markdown("Gooi een renner eruit en laat de AI een vervanger zoeken.")
        
        if st.session_state.last_finetune:
            st.success(f"✅ **Wijziging succesvol doorgevoerd!**\n\n❌ Eruit: {', '.join(st.session_state.last_finetune['uit'])}\n\n📥 Erin: {', '.join(st.session_state.last_finetune['in'])}")
            st.session_state.last_finetune = None 
        
        c_fine1, c_fine2 = st.columns(2, gap="small")
        with c_fine1:
            to_replace = st.multiselect("❌ Gooi eruit:", options=all_display_riders)
        with c_fine2:
            available_replacements = [r for r in df['Renner'].tolist() if r not in all_display_riders]
            to_add_manual = st.multiselect("📥 Zoek zelf een vervanger (optioneel):", options=available_replacements)
            
        to_add = to_add_manual.copy()
            
        if to_replace:
            freed_budget = df[df['Renner'].isin(to_replace)]['Prijs'].sum()
            current_leftover = max_bud - start_team_df['Prijs'].sum()
            max_affordable = freed_budget + current_leftover
            
            sugg_df = df[~df['Renner'].isin(all_display_riders)].copy()
            sugg_df = sugg_df[sugg_df['Prijs'] <= max_affordable].sort_values(by='Scorito_EV', ascending=False).head(5)
            
            if not sugg_df.empty:
                st.info(f"💡 **Top 5 suggesties op basis van EV (Max budget voor 1 renner: € {max_affordable:,.0f}):**")
                sugg_display = sugg_df[['Renner', 'Prijs', 'Waarde (EV/M)', 'Scorito_EV', 'COB', 'HLL', 'SPR', 'AVG']]
                st.dataframe(sugg_display, hide_index=True, use_container_width=True)
                
                sugg_keuze = st.multiselect("👉 Of selecteer hier direct één of meer suggesties:", options=sugg_df['Renner'].tolist())
                to_add = list(set(to_add + sugg_keuze))
                
        # --- ROLLEN FORCEREN (VERBORGEN IN EXPANDER) ---
        force_new_base, force_new_uit, force_new_in = [], [], []
        freeze_others = True
        is_forcing_roles = False
        
        with st.expander("🛠️ Geavanceerd: Rol van een specifieke renner forceren"):
            st.write("Dwing het algoritme om een renner een specifieke wissel-rol te geven.")
            c_r1, c_r2, c_r3 = st.columns(3)
            with c_r1:
                force_new_base = st.multiselect("🛡️ Maak BASIS", options=list(set(all_display_riders + to_add)))
            with c_r2:
                force_new_uit = st.multiselect("❌ Maak VERKOPEN na PR", options=[r for r in list(set(all_display_riders + to_add)) if r not in force_new_base])
            with c_r3:
                force_new_in = st.multiselect("📥 Maak INKOPEN na PR", options=[r for r in list(set(all_display_riders + to_add)) if r not in force_new_base + force_new_uit])
                
            is_forcing_roles = bool(force_new_base or force_new_uit or force_new_in)
            freeze_others = st.checkbox("🔒 Bevries de rollen van mijn overige renners", value=not is_forcing_roles, help="Vink dit UIT als je de AI de ruimte wilt geven om de rollen van je andere renners te herschikken zodat je nieuwe wens wiskundig past.")

        # --- VERGELIJKING ---
        if to_replace or to_add or is_forcing_roles:
            st.markdown("**📊 Vergelijking geselecteerde renners:**")
            compare_riders = list(set(to_replace + to_add + force_new_base + force_new_uit + force_new_in))
            compare_df = df[df['Renner'].isin(compare_riders)].copy()
            
            compare_cols = ['Renner', 'Prijs', 'Waarde (EV/M)', 'Scorito_EV', 'COB', 'HLL', 'SPR', 'AVG'] + race_cols
            comp_display = compare_df[compare_cols].copy()
            
            def mark_status(renner):
                if renner in to_replace: return '❌ Eruit'
                if renner in to_add: return '📥 Erin'
                if renner in force_new_base: return '🔄 Basis'
                if renner in force_new_uit: return '🔄 Verkopen'
                if renner in force_new_in: return '🔄 Kopen'
                return ''
                
            comp_display.insert(1, 'Actie / Rol', comp_display['Renner'].apply(mark_status))
            comp_display[race_cols] = comp_display[race_cols].applymap(lambda x: '✅' if x == 1 else '-')
            
            def style_compare(row):
                if row['Actie / Rol'] == '❌ Eruit' or row['Actie / Rol'] == '🔄 Verkopen':
                    return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row)
                if row['Actie / Rol'] == '📥 Erin' or row['Actie / Rol'] == '🔄 Kopen':
                    return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row)
                return ['background-color: rgba(173, 216, 230, 0.2)'] * len(row)
                
            st.dataframe(comp_display.style.apply(style_compare, axis=1), hide_index=True, use_container_width=True)

        st.write("") 
        if st.button("🚀 Voer wijziging door en bereken", use_container_width=True):
            if not to_replace and not to_add and not is_forcing_roles:
                st.warning("Kies minimaal één wijziging in renners of rollen.")
            else:
                old_team = set(all_display_riders)
                to_keep = [r for r in all_display_riders if r not in to_replace]
                
                frozen_x, frozen_y, frozen_z = [], [], []
                force_any = []
                
                all_to_process = list(set(to_keep + to_add))
                
                for r in all_to_process:
                    if r in force_new_base:
                        frozen_x.append(r)
                    elif r in force_new_uit:
                        frozen_y.append(r)
                    elif r in force_new_in:
                        frozen_z.append(r)
                    else:
                        if freeze_others and r in current_df['Renner'].values:
                            rol = current_df[current_df['Renner'] == r]['Rol'].values[0]
                            if rol == 'Basis': frozen_x.append(r)
                            elif rol == 'Verkopen na PR': frozen_y.append(r)
                            elif rol == 'Kopen na PR': frozen_z.append(r)
                        else:
                            force_any.append(r)
                
                new_res, new_plan = solve_knapsack_with_transfers(
                    df, max_bud, min_bud, max_ren, min_per_koers, 
                    force_early, ban_early, list(set(exclude_list + to_replace)), 
                    frozen_x, frozen_y, frozen_z, force_any,
                    early_races, late_races, use_transfers
                )
                
                if new_res:
                    new_team = set(new_res)
                    if new_plan:
                        new_team.update(new_plan['in'])
                        
                    out_riders = list(old_team - new_team)
                    in_riders = list(new_team - old_team)
                    st.session_state.last_finetune = {"uit": out_riders, "in": in_riders}
                    
                    st.session_state.selected_riders = new_res
                    st.session_state.transfer_plan = new_plan
                    st.rerun()
                else:
                    st.error("Geen oplossing mogelijk! De limieten (zoals max 3 wissels of budget) zijn overschreden. Tip: Zet het vinkje 'Bevries rollen' uit.")

        # 3. MATRIX
        st.header("🗓️ 3. Startlijst Matrix (Seizoensoverzicht)")
        matrix_df = current_df[['Renner', 'Rol', 'Type', 'Team', 'Prijs'] + race_cols].set_index('Renner')
        
        active_matrix = matrix_df.copy()
        if st.session_state.transfer_plan:
            for r in early_races:
                active_matrix.loc[active_matrix['Rol'] == 'Kopen na PR', r] = 0
            for r in late_races:
                active_matrix.loc[active_matrix['Rol'] == 'Verkopen na PR', r] = 0

        display_matrix = matrix_df[race_cols].applymap(lambda x: '✅' if x == 1 else '-')
        display_matrix.insert(0, 'Rol', matrix_df['Rol'])
        display_matrix.insert(1, 'Type', matrix_df['Type'])
        display_matrix.insert(2, 'Team', matrix_df['Team'])
        display_matrix.insert(3, 'Prijs', matrix_df['Prijs'].apply(lambda x: f"€ {x/1000000:.2f}M"))
        display_matrix.insert(4, 'Koersen', active_matrix[race_cols].sum(axis=1).astype(int))
        
        if 'PR' in display_matrix.columns:
            pr_idx = display_matrix.columns.get_loc('PR')
            display_matrix.insert(pr_idx + 1, '🔁', '|')
            
        totals_dict = {}
        for c in display_matrix.columns:
            if c in race_cols:
                totals_dict[c] = str(int(active_matrix[c].sum()))
            elif c == '🔁':
                totals_dict[c] = '|'
            elif c == 'Rol':
                totals_dict[c] = 'TOTAAL ACTIEF'
            else:
                totals_dict[c] = ''
                
        display_matrix.loc['🏆 TOTAAL AAN DE START'] = pd.Series(totals_dict)

        def style_rows(row):
            if row.name == '🏆 TOTAAL AAN DE START':
                return ['background-color: rgba(255, 215, 0, 0.2); font-weight: bold; border-top: 2px solid black'] * len(row)
            if row['Rol'] == 'Verkopen na PR':
                return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row)
            elif row['Rol'] == 'Kopen na PR':
                return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row)
            return [''] * len(row)

        styled_matrix = display_matrix.style.apply(style_rows, axis=1)
        st.dataframe(styled_matrix, use_container_width=True)

        # 4. KOPMAN
        st.header("🥇 4. Kopman Advies (Actieve renners)")
        kop_res = []
        for c in race_cols:
            starters = active_matrix[active_matrix[c] == 1]
            if not starters.empty:
                stat = koers_mapping.get(c, 'AVG')
                starters_stats = current_df[current_df['Renner'].isin(starters.index)]
                top = starters_stats.sort_values(by=[stat, 'AVG'], ascending=False)['Renner'].tolist()
                kop_res.append({"Koers": c, "K1": top[0] if len(top)>0 else "-", "K2": top[1] if len(top)>1 else "-", "K3": top[2] if len(top)>2 else "-"})
        st.dataframe(pd.DataFrame(kop_res), hide_index=True, use_container_width=True)

        # 5. STATS
        st.header("📊 5. Team Statistieken")
        stats_overzicht = current_df[['Renner', 'Rol', 'Type', 'Team', 'Prijs', 'Waarde (EV/M)', 'EV_early', 'EV_late', 'Scorito_EV']].copy()
        
        stats_overzicht = stats_overzicht.rename(columns={
            'EV_early': 'EV Early', 
            'EV_late': 'EV Late', 
            'Scorito_EV': 'Scorito EV'
        })
        
        def style_stats(row):
            if row['Rol'] == 'Verkopen na PR':
                return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row)
            elif row['Rol'] == 'Kopen na PR':
                return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row)
            return [''] * len(row)
            
        styled_stats = stats_overzicht.sort_values(by=['Rol', 'Scorito EV'], ascending=[True, False]).style.apply(style_stats, axis=1)
        st.dataframe(styled_stats, hide_index=True, use_container_width=True)

with tab2:
    st.header("📋 Alle Renners & Programma's")
    st.markdown("Zoek door de volledige database van renners, filter op budget of zoek een renner voor een specifiek gat in je programma.")
    
    with st.expander("📅 Legenda Koersen (Overzicht)"):
        koersen_info = [
            {"Afkorting": "OHN", "Koers": "Omloop Het Nieuwsblad", "Type": "Kassei (COB)"},
            {"Afkorting": "KBK", "Koers": "Kuurne-Brussel-Kuurne", "Type": "Sprint (SPR)"},
            {"Afkorting": "SB", "Koers": "Strade Bianche", "Type": "Heuvel (HLL)"},
            {"Afkorting": "PN", "Koers": "Parijs-Nice (Etappe 7)", "Type": "Heuvel (HLL)"},
            {"Afkorting": "TA", "Koers": "Tirreno-Adriatico (Etappe 7)", "Type": "Sprint (SPR)"},
            {"Afkorting": "MSR", "Koers": "Milaan-San Remo", "Type": "Allround (AVG)"},
            {"Afkorting": "BDP", "Koers": "Classic Brugge-De Panne", "Type": "Sprint (SPR)"},
            {"Afkorting": "E3", "Koers": "E3 Saxo Classic", "Type": "Kassei (COB)"},
            {"Afkorting": "GW", "Koers": "Gent-Wevelgem", "Type": "Sprint (SPR)"},
            {"Afkorting": "DDV", "Koers": "Dwars door Vlaanderen", "Type": "Kassei (COB)"},
            {"Afkorting": "RVV", "Koers": "Ronde van Vlaanderen", "Type": "Kassei (COB)"},
            {"Afkorting": "SP", "Koers": "Scheldeprijs", "Type": "Sprint (SPR)"},
            {"Afkorting": "PR", "Koers": "Parijs-Roubaix", "Type": "Kassei (COB)"},
            {"Afkorting": "BP", "Koers": "Brabantse Pijl", "Type": "Heuvel (HLL)"},
            {"Afkorting": "AGR", "Koers": "Amstel Gold Race", "Type": "Heuvel (HLL)"},
            {"Afkorting": "WP", "Koers": "Waalse Pijl", "Type": "Heuvel (HLL)"},
            {"Afkorting": "LBL", "Koers": "Luik-Bastenaken-Luik", "Type": "Heuvel (HLL)"}
        ]
        st.dataframe(pd.DataFrame(koersen_info), hide_index=True, use_container_width=True)
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        search_name = st.text_input("🔍 Zoek op naam of Ploeg:")
    
    with col_f2:
        min_p = int(df['Prijs'].min())
        max_p = int(df['Prijs'].max())
        price_filter = st.slider("💰 Prijs range", min_value=min_p, max_value=max_p, value=(min_p, max_p), step=250000)
        
    with col_f3:
        race_filter = st.multiselect("🏁 Rijdt ALLE geselecteerde koersen:", options=race_cols)

    filtered_df = df.copy()
    filtered_df['Type'] = filtered_df.apply(bepaal_klassieker_type, axis=1)
    
    if search_name:
        filtered_df = filtered_df[
            filtered_df['Renner'].str.contains(search_name, case=False, na=False) |
            filtered_df['Team'].str.contains(search_name, case=False, na=False)
        ]
        
    filtered_df = filtered_df[(filtered_df['Prijs'] >= price_filter[0]) & (filtered_df['Prijs'] <= price_filter[1])]
    
    if race_filter:
        filtered_df = filtered_df[filtered_df[race_filter].sum(axis=1) == len(race_filter)]

    display_cols = ['Renner', 'Team', 'Prijs', 'Waarde (EV/M)', 'Type', 'Total_Races', 'Scorito_EV'] + race_cols
    display_df = filtered_df[display_cols].copy()
    
    display_df = display_df.rename(columns={
        'Total_Races': 'Total Races', 
        'Scorito_EV': 'Scorito EV'
    })
    
    display_df = display_df.sort_values(by='Scorito EV', ascending=False)
    
    display_df[race_cols] = display_df[race_cols].applymap(lambda x: '✅' if x == 1 else '-')
    
    if 'PR' in display_df.columns:
        pr_idx = display_df.columns.get_loc('PR')
        display_df.insert(pr_idx + 1, '🔁', '|')
        
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab3:
    st.header("ℹ️ Hoe werkt deze Solver?")
    st.markdown("""
    Deze applicatie berekent wiskundig het meest optimale Scorito-team voor het Voorjaarsklassiekers-spel. Het haalt de emotie uit het spel en kijkt puur naar statistieken en wedstrijdprogramma's.
    
    ### 1. Rekenmodellen (EV Berekening)
    Je kunt in het linker zijmenu exact kiezen hoe het algoritme de Verwachte Punten (EV) per renner berekent. Elke methode heeft een eigen wiskundige visie op de koers:
    
    * **1. Scorito Ranking (Dynamisch):** Sorteert de startlijst puur op basis van de stats en deelt exacte Scorito-punten uit (100 voor de #1, 90 voor de #2, etc.). Dit is perfect om het Scorito-spel exact na te bootsen, maar gaat er wel van uit dat de uitslag van een wielerwedstrijd 100% voorspelbaar is.
    * **2. Originele Curve (Macht 4):** Gebruikt de formule `(Stat / 100)⁴ × 100`. Dit creëert een vloeiende exponentiële lijn waarbij topspecialisten veel punten krijgen en allrounders wat minder. Dit is de vertrouwde en bewezen standaardmethode van de applicatie.
    * **3. Extreme Curve (Macht 10):** Gebruikt een veel agressievere machtsformule (`¹⁰`). Knechten en opvullers worden genadeloos afgestraft en vallen terug naar 0 punten. Alleen de absolute wereldtop houdt EV over in dit model.
    * **4. Tiers & Spreiding (Realistisch):** Wielrennen is chaotisch en onvoorspelbaar. Deze methode deelt de startlijst op in 'Tiers'. De absolute top 3 krijgt gemiddeld 80 EV, nummers 4 t/m 8 krijgen 45 EV, en 9 t/m 15 krijgen 20 EV. Hiermee simuleer je dat een topfavoriet ook wel eens valt of lek rijdt.
    
    *Let op: In **alle** rekenmethodes krijgen de top 3 favorieten op de startlijst automatisch de Scorito Kopman-bonus (x3, x2.5 en x2) over hun EV berekend. Zo dwingt de app je om voor dure zekere kopmannen te gaan.*
    
    ### 2. Het Algoritme (Knapsack Problem)
    Om van al deze individuele waarden tot het beste team van 20 renners te komen, gebruiken we een wiskundig principe genaamd het **Knapsack Problem** (krukzakprobleem). 
    
    Je kunt dit zien als een rugzak (het budget van €45.000.000) die je wilt vullen met items (renners). Je wilt de rugzak zo vullen dat de totale waarde (EV) zo hoog mogelijk is, zonder dat de rugzak scheurt (over budget gaat) en waarbij precies 20 items in de tas passen. De Python-module *Pulp* rekent razendsnel alle miljoenen mogelijke combinaties door en geeft de wiskundig perfecte uitkomst.
    """)
    
    st.markdown("""
    ### 3. Wisselstrategie (Transfers)
    Als je de wissel-optie aanzet, verdeelt het algoritme de agenda in twee periodes:
    * **Early:** Alle koersen t/m Parijs-Roubaix.
    * **Late:** Alle koersen vanaf de Brabantse Pijl (de heuvelklassiekers).
    
    Het algoritme kiest in dit geval geen 20, maar in totaal 23 renners. Het zoekt naar de optimale combinatie van 17 'vaste' renners die de hele periode blijven, 3 'tijdelijke' renners die veel EV opleveren in het begin, en 3 'vervangers' die de pieken pakken in de Ardennen.
    """)
    
    st.divider()
    
    st.header("🙏 Databronnen & Credits")
    st.markdown("""
    Zonder de data uit de community was deze tool niet mogelijk geweest. Veel dank aan:
    
    - **📊 Statistieken:** [Wielerorakel](https://www.cyclingoracle.com/) levert de onmisbare, actuele skill-scores (COB, HLL, SPR, AVG, MTN, ITT, GC) per renner.
    - **🗓️ Programma's & Prijzen:** [Kopman Puzzel](https://kopmanpuzzel.up.railway.app/) verzamelt en structureert de voorlopige startlijsten en Scorito-prijzen.
    """)
