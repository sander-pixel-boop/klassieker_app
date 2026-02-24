import streamlit as st
import pandas as pd
import pulp
import json
import google.generativeai as genai
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Klassiekers Team", layout="wide", page_icon="🚴‍♂️")

# --- DATA LADEN ---
@st.cache_data
def load_and_merge_data():
    try:
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', on_bad_lines='skip')
        df_prog.loc[df_prog['Prijs'] == 800000, 'Prijs'] = 750000
        
        df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
            
        df_stats = df_stats.drop_duplicates(subset=['Renner'], keep='first')
        
        short_names = df_prog['Renner'].unique()
        full_names = df_stats['Renner'].unique()
        name_mapping = {}
        
        manual_overrides = {
            "Poel": "Mathieu van der Poel", "Aert": "Wout van Aert", "Lie": "Arnaud De Lie",
            "Gils": "Maxim Van Gils", "Berg": "Marijn van den Berg", "Broek": "Frank van den Broek",
            "Magnier": "Paul Magnier", "Pogacar": "Tadej Pogačar", "Skujins": "Toms Skujiņš",
            "Kooij": "Olav Kooij"
        }
        
        for short in short_names:
            if short in manual_overrides:
                name_mapping[short] = manual_overrides[short]
            else:
                match_res = process.extractOne(short, full_names, scorer=fuzz.token_set_ratio)
                name_mapping[short] = match_res[0] if match_res and match_res[1] > 75 else short

        df_prog['Renner_Full'] = df_prog['Renner'].map(name_mapping)
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 1500000), 'Renner_Full'] = 'Florian Vermeersch'
        df_prog.loc[(df_prog['Renner'] == 'Vermeersch') & (df_prog['Prijs'] == 750000), 'Renner_Full'] = 'Gianni Vermeersch'
        
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
        
        for col in available_races + ['COB', 'HLL', 'SPR', 'AVG', 'Prijs']:
            if col not in merged_df.columns:
                merged_df[col] = 0
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0).astype(int)
        
        merged_df['Total_Races'] = merged_df[available_races].sum(axis=1).astype(int)
        
        koers_stat_map = {'OHN':'COB','KBK':'SPR','SB':'HLL','PN':'HLL','TA':'SPR','MSR':'AVG','BDP':'SPR','E3':'COB','GW':'SPR','DDV':'COB','RVV':'COB','SP':'SPR','PR':'COB','BP':'HLL','AGR':'HLL','WP':'HLL','LBL':'HLL'}
        
        merged_df['EV_early'] = 0.0
        for koers in available_early:
            stat = koers_stat_map.get(koers, 'AVG')
            merged_df['EV_early'] += merged_df[koers] * ((merged_df[stat] / 100)**4 * 100)
            
        merged_df['EV_late'] = 0.0
        for koers in available_late:
            stat = koers_stat_map.get(koers, 'AVG')
            merged_df['EV_late'] += merged_df[koers] * ((merged_df[stat] / 100)**4 * 100)

        merged_df['EV_early'] = merged_df['EV_early'].fillna(0).round(0).astype(int)
        merged_df['EV_late'] = merged_df['EV_late'].fillna(0).round(0).astype(int)
        merged_df['Scorito_EV'] = merged_df['EV_early'] + merged_df['EV_late']
        
        return merged_df, available_early, available_late, koers_stat_map
    except Exception as e:
        st.error(f"Fout in dataverwerking: {e}")
        return pd.DataFrame(), [], [], {}

df, early_races, late_races, koers_mapping = load_and_merge_data()
race_cols = early_races + late_races

if df.empty:
    st.warning("Data is leeg of kon niet worden geladen.")
    st.stop()

if "selected_riders" not in st.session_state:
    st.session_state.selected_riders = []
if "transfer_plan" not in st.session_state:
    st.session_state.transfer_plan = None
if "last_finetune" not in st.session_state:
    st.session_state.last_finetune = None
if "gemini_history" not in st.session_state:
    st.session_state.gemini_history = [{"role": "assistant", "content": "Hoi! Plak je API-sleutel hierboven en vraag me alles over je Scorito-team."}]

# --- SOLVER MET WISSELS ---
def solve_knapsack_with_transfers(dataframe, total_budget, min_budget, max_riders, min_per_race, force_list, exclude_list, early_races, late_races, use_transfers):
    prob = pulp.LpProblem("Scorito_Solver", pulp.LpMaximize)
    
    if use_transfers:
        x = pulp.LpVariable.dicts("Base", dataframe.index, cat='Binary')
        y = pulp.LpVariable.dicts("Early", dataframe.index, cat='Binary')
        z = pulp.LpVariable.dicts("Late", dataframe.index, cat='Binary')
        
        prob += pulp.lpSum([x[i] * dataframe.loc[i, 'Scorito_EV'] + y[i] * dataframe.loc[i, 'EV_early'] + z[i] * dataframe.loc[i, 'EV_late'] for i in dataframe.index])
        
        for i in dataframe.index:
            prob += x[i] + y[i] + z[i] <= 1
            if dataframe.loc[i, 'Renner'] in force_list:
                prob += x[i] + y[i] + z[i] == 1
            if dataframe.loc[i, 'Renner'] in exclude_list:
                prob += x[i] + y[i] + z[i] == 0

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
            if dataframe.loc[i, 'Renner'] in force_list: prob += rider_vars[i] == 1
            if dataframe.loc[i, 'Renner'] in exclude_list: prob += rider_vars[i] == 0
        
        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=15))
        if pulp.LpStatus[prob.status] == 'Optimal':
            selected = [dataframe.loc[i, 'Renner'] for i in dataframe.index if rider_vars[i].varValue > 0.5]
            return selected[:max_riders], None
            
    return None, None

# --- UI TABS ---
st.title("🏆 Klassiekers Team")

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Team Builder", "📋 Alle Renners", "💬 Gemini Vraagbaak", "ℹ️ Uitleg & Credits"])

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
        force_list = st.multiselect("🔒 Forceer:", options=df['Renner'].tolist())
        exclude_list = st.multiselect("❌ Sluit uit:", options=[r for r in df['Renner'].tolist() if r not in force_list])

        if st.button("🚀 Bereken Optimaal Team", type="primary", use_container_width=True):
            st.session_state.last_finetune = None
            res, transfer_plan = solve_knapsack_with_transfers(df, max_bud, min_bud, max_ren, min_per_koers, force_list, exclude_list, early_races, late_races, use_transfers)
            if res:
                st.session_state.selected_riders = res
                st.session_state.transfer_plan = transfer_plan
                st.rerun()
            else:
                st.error("Geen oplossing mogelijk. Probeer de eisen te versoepelen.")
                
        # --- OPSLAAN / LADEN BLOK ---
        st.divider()
        with st.expander("💾 Team Opslaan / Inladen"):
            if st.session_state.selected_riders:
                save_data = {
                    "selected_riders": st.session_state.selected_riders,
                    "transfer_plan": st.session_state.transfer_plan
                }
                json_str = json.dumps(save_data)
                st.download_button(
                    label="📥 Download huidig team",
                    data=json_str,
                    file_name="scorito_team.json",
                    mime="application/json",
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

    # --- RESULTATEN ---
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

        # --- FINETUNER BLOK ---
        st.divider()
        st.header("🔄 2. Team Finetunen")
        st.markdown("Is de AI met een renner gekomen die je er eigenlijk niet in wil hebben? Kies hem hieronder en laat de AI direct de beste vervanger zoeken binnen je restbudget.")
        
        if st.session_state.last_finetune:
            st.success(f"✅ **Wissel succesvol doorgevoerd!**\n\n❌ Eruit: {', '.join(st.session_state.last_finetune['uit'])}\n\n📥 Erin: {', '.join(st.session_state.last_finetune['in'])}")
            st.session_state.last_finetune = None 
        
        c_fine1, c_fine2 = st.columns([3, 1], gap="small")
        with c_fine1:
            to_replace = st.multiselect("Gooi deze renner(s) eruit:", options=all_display_riders)
        with c_fine2:
            st.write("") 
            st.write("")
            if st.button("Zoek vervanger(s)", use_container_width=True):
                if not to_replace:
                    st.warning("Kies eerst een renner.")
                else:
                    old_team = set(all_display_riders)
                    
                    to_keep = [r for r in all_display_riders if r not in to_replace]
                    new_force = list(set(force_list + to_keep))
                    new_exclude = list(set(exclude_list + to_replace))
                    
                    new_res, new_plan = solve_knapsack_with_transfers(
                        df, max_bud, min_bud, max_ren, min_per_koers, 
                        new_force, new_exclude, early_races, late_races, use_transfers
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
                        st.error("Geen mogelijke vervanger gevonden! Check of je Minimum Budget niet te hoog staat in de linkerbalk.")

        def color_rows(row):
            if row['Rol'] == 'Verkopen na PR':
                return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row)
            elif row['Rol'] == 'Kopen na PR':
                return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row)
            return [''] * len(row)

        # 3. MATRIX
        st.header("🗓️ 3. Startlijst Matrix (Seizoensoverzicht)")
        matrix_df = current_df[['Renner', 'Rol'] + race_cols].set_index('Renner')
        
        active_matrix = matrix_df.copy()
        if st.session_state.transfer_plan:
            for r in early_races:
                active_matrix.loc[active_matrix['Rol'] == 'Kopen na PR', r] = 0
            for r in late_races:
                active_matrix.loc[active_matrix['Rol'] == 'Verkopen na PR', r] = 0

        totals = active_matrix[race_cols].sum().astype(int).astype(str)
        totals_dict = totals.to_dict()
        
        if 'PR' in race_cols:
            new_totals = {}
            for k, v in totals_dict.items():
                new_totals[k] = v
                if k == 'PR':
                    new_totals['🔁'] = ''
            totals_row = pd.DataFrame([new_totals], index=['🏆 TOTAAL AAN DE START (Actief)'])
        else:
            totals_row = pd.DataFrame([totals_dict], index=['🏆 TOTAAL AAN DE START (Actief)'])
            
        st.dataframe(totals_row, use_container_width=True)

        display_matrix = matrix_df[race_cols].applymap(lambda x: '✅' if x == 1 else '-')
        display_matrix.insert(0, 'Rol', matrix_df['Rol'])
        
        if 'PR' in display_matrix.columns:
            pr_idx = display_matrix.columns.get_loc('PR')
            display_matrix.insert(pr_idx + 1, '🔁', '|')
        
        styled_matrix = display_matrix.style.apply(color_rows, axis=1)
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
        stats_overzicht = current_df[['Renner', 'Rol', 'COB', 'HLL', 'SPR', 'AVG', 'Prijs', 'EV_early', 'EV_late', 'Scorito_EV']].copy()
        
        stats_overzicht = stats_overzicht.rename(columns={
            'EV_early': 'EV Early', 
            'EV_late': 'EV Late', 
            'Scorito_EV': 'Scorito EV'
        })
        
        styled_stats = stats_overzicht.sort_values(by=['Rol', 'Scorito EV'], ascending=[True, False]).style.apply(color_rows, axis=1)
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
        search_name = st.text_input("🔍 Zoek op naam:")
    
    with col_f2:
        min_p = int(df['Prijs'].min())
        max_p = int(df['Prijs'].max())
        price_filter = st.slider("💰 Prijs range", min_value=min_p, max_value=max_p, value=(min_p, max_p), step=250000)
        
    with col_f3:
        race_filter = st.multiselect("🏁 Rijdt ALLE geselecteerde koersen:", options=race_cols)

    filtered_df = df.copy()
    
    if search_name:
        filtered_df = filtered_df[filtered_df['Renner'].str.contains(search_name, case=False, na=False)]
        
    filtered_df = filtered_df[(filtered_df['Prijs'] >= price_filter[0]) & (filtered_df['Prijs'] <= price_filter[1])]
    
    if race_filter:
        filtered_df = filtered_df[filtered_df[race_filter].sum(axis=1) == len(race_filter)]

    display_cols = ['Renner', 'Prijs', 'Total_Races', 'Scorito_EV'] + race_cols
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
    st.header("💬 Gemini Vraagbaak")
    st.markdown("Koppel deze app aan Gemini om complexe vragen over je renners te stellen. Haal een gratis API-sleutel op via [Google AI Studio](https://aistudio.google.com/).")
    
    api_key = st.text_input("🔑 Gemini API Key:", type="password")
    
    for msg in st.session_state.gemini_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Vraag Gemini iets over de renners..."):
        st.session_state.gemini_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not api_key:
            response = "Vul eerst je API-sleutel in bovenaan deze pagina."
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.gemini_history.append({"role": "assistant", "content": response})
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                
                context_cols = ['Renner', 'Prijs', 'Scorito_EV', 'COB', 'HLL', 'SPR', 'AVG'] + race_cols
                data_context = df[context_cols].to_csv(index=False)
                
                full_prompt = f"Je bent een ploegleider assistent voor het Scorito Klassiekerspel. Geef korte, directe antwoorden. Gebruik de volgende data:\n\n{data_context}\n\nVraag van gebruiker: {prompt}"
                
                ai_response = model.generate_content(full_prompt)
                response = ai_response.text

                with st.chat_message("assistant"):
                    st.markdown(response)
                st.session_state.gemini_history.append({"role": "assistant", "content": response})
                
            except Exception as e:
                st.error(f"Fout met de Gemini API: {e}")

with tab4:
    st.header("ℹ️ Hoe werkt deze Solver?")
    st.markdown("""
    Deze applicatie berekent wiskundig het meest optimale Scorito-team voor het Voorjaarsklassiekers-spel.
    
    1. **Data:** De app matcht de startlijsten, renner-statistieken (zoals sprint-, kassei- en heuvelkwaliteiten) en de Scorito-prijzen.
    2. **Expected Value (EV):** Elke renner krijgt een berekende 'Expected Value' per koers, afhankelijk van het type parcours en zijn specifieke stats.
    3. **Optimalisatie:** Met behulp van een zogeheten *Knapsack Algorithm* berekent de AI exact welke 20 renners binnen jouw budget de hoogst mogelijke EV opleveren. 
    4. **Wisselstrategie:** Als je de wissel-optie aanzet, verdeelt het algoritme de EV over de periode *tot* Parijs-Roubaix en *vanaf* de Brabantse Pijl, om zo de ultieme 3 in- en uitgaande transfers te bereken.
    
    *Je kunt zelf renners uitsluiten of juist forceren om het model richting jouw persoonlijke voorkeur te sturen.*
    """)
    
    st.divider()
    
    st.header("🙏 Shout-outs & Credits")
    st.markdown("""
    Zonder de data uit de community was deze tool niet mogelijk geweest. Veel dank aan:
    
    - **📊 Statistieken:** [Wielerorakel](https://www.cyclingoracle.com/) voor de uitgebreide en super accurate stats per renner.
    - **🗓️ Programma's & Prijzen:** [Kopman Puzzel](https://kopmanpuzzel.up.railway.app/) voor het verzamelen en overzichtelijk maken van de startlijsten en Scorito-prijzen.
    """)
