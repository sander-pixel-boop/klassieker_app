import streamlit as st
import pandas as pd
import pulp
import json
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Scorito Klassiekers AI", layout="wide", page_icon="🏆")

# --- HULPFUNCTIE: NORMALISATIE (Leestekens verwijderen) ---
def normalize_name_logic(text):
    if not isinstance(text, str):
        return ""
    # Omzetten naar kleine letters, witruimte trimmen en accenten verwijderen
    text = text.lower().strip()
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# --- DATA LADEN (KLASSIEKERS SCORITO) ---
@st.cache_data
def load_and_merge_data():
    try:
        # 1. Programma inladen (met UTF-8-sig voor Excel compatibiliteit)
        df_prog = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
        df_prog = df_prog.rename(columns={'RvB': 'BDP', 'IFF': 'GW'})
        
        # Prijs extractie
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
        
        # 2. Stats inladen
        df_stats = pd.read_csv("renners_stats.csv", sep='\t', encoding='utf-8-sig') 
        if 'Naam' in df_stats.columns: df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        if 'Team' not in df_stats.columns and 'Ploeg' in df_stats.columns: df_stats = df_stats.rename(columns={'Ploeg': 'Team'})
        df_stats = df_stats.drop_duplicates(subset=['Renner'], keep='first')
        
        # 3. NAAM MATCHING MET NORMALISATIE (Küng -> Kung)
        short_names = df_prog['Renner'].unique()
        full_names = df_stats['Renner'].unique()
        
        # Map voor genormaliseerde namen naar originele database namen
        norm_to_full = {normalize_name_logic(n): n for n in full_names}
        norm_full_names = list(norm_to_full.keys())
        
        name_mapping = {}
        manual_overrides = {
            "Poel": "Mathieu van der Poel", "Aert": "Wout van Aert", "Lie": "Arnaud De Lie",
            "Gils": "Maxim Van Gils", "Broek": "Frank van den Broek", "Pogacar": "Tadej Pogačar"
        }
        
        for short in short_names:
            if short in manual_overrides:
                name_mapping[short] = manual_overrides[short]
            else:
                norm_short = normalize_name_logic(short)
                match_res = process.extractOne(norm_short, norm_full_names, scorer=fuzz.token_set_ratio)
                if match_res and match_res[1] > 75:
                    name_mapping[short] = norm_to_full[match_res[0]]
                else:
                    name_mapping[short] = short

        df_prog['Renner_Full'] = df_prog['Renner'].map(name_mapping)
        merged_df = pd.merge(df_prog, df_stats, left_on='Renner_Full', right_on='Renner', how='left')
        
        if 'Renner_x' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Renner_x', 'Renner_y'], errors='ignore')
            
        merged_df = merged_df.sort_values(by='Prijs', ascending=False)
        merged_df = merged_df.drop_duplicates(subset=['Renner_Full'], keep='first')
        merged_df = merged_df.rename(columns={'Renner_Full': 'Renner'})
        
        early_races = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'BDP', 'E3', 'GW', 'DDV', 'RVV', 'SP', 'PR']
        late_races = ['BP', 'AGR', 'WP', 'LBL']
        available_races = [k for k in early_races + late_races if k in merged_df.columns]
        
        for col in available_races + ['Prijs', 'COB', 'HLL', 'SPR', 'AVG', 'MTN']:
            if col in merged_df.columns:
                merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0).astype(int)
            
        merged_df['HLL/MTN'] = merged_df[['HLL', 'MTN']].max(axis=1).astype(int)
        merged_df['Total_Races'] = merged_df[available_races].sum(axis=1).astype(int)
        merged_df['Team'] = merged_df['Team'].fillna('Onbekend')
        
        koers_stat_map = {'OHN':'COB','KBK':'SPR','SB':'HLL','PN':'HLL/MTN','TA':'SPR','MSR':'AVG','BDP':'SPR','E3':'COB','GW':'SPR','DDV':'COB','RVV':'COB','SP':'SPR','PR':'COB','BP':'HLL','AGR':'HLL','WP':'HLL','LBL':'HLL'}
        
        return merged_df, early_races, late_races, koers_stat_map
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
            if "Scorito Ranking" in method: val = scorito_pts[i] if i < 20 else 0.0
            elif "Originele Curve" in method: val = (starters.loc[idx, stat] / 100)**4 * 100
            if i == 0: val *= 3.0
            elif i == 1: val *= 2.5
            elif i == 2: val *= 2.0
            race_ev.loc[idx] = val
        return race_ev

    for koers in early_races: df['EV_early'] += get_race_ev(koers)
    for koers in late_races: df['EV_late'] += get_race_ev(koers)
    df['Scorito_EV'] = (df['EV_early'] + df['EV_late']).round(0).astype(int)
    df['Waarde (EV/M)'] = (df['Scorito_EV'] / (df['Prijs'] / 1000000)).replace([float('inf')], 0).fillna(0).round(1)
    return df

# --- SOLVER ---
def solve_knapsack_with_transfers(dataframe, total_budget, max_riders, frozen_x, frozen_y, frozen_z, exclude_list):
    prob = pulp.LpProblem("Scorito_Solver", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("Base", dataframe.index, cat='Binary')
    y = pulp.LpVariable.dicts("Early", dataframe.index, cat='Binary')
    z = pulp.LpVariable.dicts("Late", dataframe.index, cat='Binary')
    
    prob += pulp.lpSum([x[i] * dataframe.loc[i, 'Scorito_EV'] + y[i] * dataframe.loc[i, 'EV_early'] + z[i] * dataframe.loc[i, 'EV_late'] for i in dataframe.index])
    
    for i in dataframe.index:
        r = dataframe.loc[i, 'Renner']
        prob += x[i] + y[i] + z[i] <= 1
        if r in exclude_list: prob += x[i] + y[i] + z[i] == 0
        if r in frozen_x: prob += x[i] == 1
        if r in frozen_y: prob += y[i] == 1
        if r in frozen_z: prob += z[i] == 1

    prob += pulp.lpSum([x[i] for i in dataframe.index]) == max_riders - 3
    prob += pulp.lpSum([y[i] for i in dataframe.index]) == 3
    prob += pulp.lpSum([z[i] for i in dataframe.index]) == 3
    prob += pulp.lpSum([(x[i] + y[i]) * dataframe.loc[i, 'Prijs'] for i in dataframe.index]) <= total_budget
    prob += pulp.lpSum([(x[i] + z[i]) * dataframe.loc[i, 'Prijs'] for i in dataframe.index]) <= total_budget
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=30))
    if pulp.LpStatus[prob.status] == 'Optimal':
        bt = [dataframe.loc[i, 'Renner'] for i in dataframe.index if x[i].varValue > 0.5]
        et = [dataframe.loc[i, 'Renner'] for i in dataframe.index if y[i].varValue > 0.5]
        lt = [dataframe.loc[i, 'Renner'] for i in dataframe.index if z[i].varValue > 0.5]
        return bt + et, {"uit": et, "in": lt}
    return None, None

def bepaal_klassieker_type(row):
    s = {'Kassei': row['COB'], 'Heuvel': row['HLL'], 'Sprint': row['SPR'], 'Klimmer': row['MTN']}
    return max(s, key=s.get)

# --- UI START ---
df_raw, early_races, late_races, koers_mapping = load_and_merge_data()
race_cols = early_races + late_races

if "selected_riders" not in st.session_state: st.session_state.selected_riders = []
if "transfer_plan" not in st.session_state: st.session_state.transfer_plan = None

with st.sidebar:
    st.title("🏆 AI Coach")
    ev_method = st.selectbox("Rekenmodel", ["Scorito Ranking", "Originele Curve"])
    max_bud = st.number_input("Max Budget", value=45000000, step=500000)
    df = calculate_ev(df_raw, early_races, late_races, koers_mapping, ev_method)
    
    if st.button("🚀 BEREKEN OPTIMAAL TEAM", type="primary", use_container_width=True):
        res, tp = solve_knapsack_with_transfers(df, max_bud, 20, [], [], [], [])
        if res: st.session_state.selected_riders, st.session_state.transfer_plan = res, tp; st.rerun()

    st.divider()
    uploaded_file = st.file_uploader("📂 Oude Teams Inladen", type="json")
    if uploaded_file is not None and st.button("Laad Backup"):
        try:
            ld = json.load(uploaded_file)
            geldige = df['Renner'].tolist()
            st.session_state.selected_riders = [r for r in ld.get("selected_riders", []) if r in geldige]
            if ld.get("transfer_plan"):
                st.session_state.transfer_plan = {k: [r for r in v if r in geldige] for k, v in ld["transfer_plan"].items()}
            st.success("Backup geladen!")
            st.rerun()
        except: st.error("Fout bij laden.")

st.title("🏆 Voorjaarsklassiekers: Scorito")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Jouw Team & Analyse", "📋 Database", "🗓️ Kalender", "ℹ️ Uitleg"])

with tab1:
    if st.session_state.selected_riders:
        all_in_sel = list(set(st.session_state.selected_riders + (st.session_state.transfer_plan['in'] if st.session_state.transfer_plan else [])))
        curr_df = df[df['Renner'].isin(all_in_sel)].copy()
        curr_df['Type'] = curr_df.apply(bepaal_klassieker_type, axis=1)

        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Budget Over", f"€ {max_bud - df[df['Renner'].isin(st.session_state.selected_riders)]['Prijs'].sum():,.0f}")
        m2.metric("🎯 Team EV", f"{curr_df['Scorito_EV'].sum():.0f}")
        m3.metric("🚴 Renners", f"{len(st.session_state.selected_riders)} / 20")

        c1, c2 = st.columns(2)
        with c1:
            avg_stats = curr_df[['COB', 'HLL', 'SPR', 'AVG']].mean()
            fig = go.Figure(go.Scatterpolar(r=avg_stats.values.tolist() + [avg_stats[0]], theta=['Kassei','Heuvel','Sprint','Allround','Kassei'], fill='toself'))
            fig.update_layout(title="Team Profiel")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig_donut = px.pie(curr_df, names='Type', values='Prijs', hole=0.4, title="Budget per Type")
            st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()
        with st.container(border=True):
            st.subheader("🛠️ Handmatige Wissel Forceerder")
            col_a, col_b = st.columns(2)
            with col_a: verkoop = st.multiselect("❌ Verkoop na PR:", st.session_state.selected_riders)
            with col_b: koop = st.multiselect("📥 Koop na PR:", [r for r in df['Renner'].tolist() if r not in all_in_sel])
            if st.button("🚀 VOER HANDMATIGE WISSEL DOOR", use_container_width=True):
                f_x = [r for r in st.session_state.selected_riders if r not in verkoop and r not in (st.session_state.transfer_plan['uit'] if st.session_state.transfer_plan else [])]
                f_y = [r for r in st.session_state.selected_riders if r in (st.session_state.transfer_plan['uit'] if st.session_state.transfer_plan else []) or r in verkoop]
                res, tp = solve_knapsack_with_transfers(df, max_bud, 20, f_x, f_y, koop, [])
                if res: st.session_state.selected_riders, st.session_state.transfer_plan = res, tp; st.rerun()

        st.subheader("🗓️ Opstellingsschema")
        matrix = curr_df[['Renner', 'Prijs', 'Team', 'Type'] + race_cols].copy()
        for c in race_cols:
            stat = koers_mapping.get(c, 'AVG')
            top = curr_df[curr_df[c]==1].sort_values(by=[stat, 'AVG'], ascending=False).head(3)['Renner'].tolist()
            matrix[c] = curr_df.apply(lambda r: 'Kopman 1' if r['Renner'] == (top[0] if top else '') else ('Kopman 2' if r['Renner'] == (top[1] if len(top)>1 else '') else ('Kopman 3' if r['Renner'] == (top[2] if len(top)>2 else '') else ('✅' if r[c]==1 else '-'))), axis=1)
        st.dataframe(matrix, use_container_width=True, hide_index=True)
    else: st.info("Bereken een team via de sidebar.")

with tab2:
    st.header("📋 Database")
    st.dataframe(df[['Renner', 'Team', 'Prijs', 'Scorito_EV', 'Waarde (EV/M)', 'COB', 'HLL', 'SPR']].sort_values(by='Scorito_EV', ascending=False), use_container_width=True, hide_index=True)

with tab3:
    st.header("🗓️ Kalender")
    st.table(pd.DataFrame([{"Koers": k, "Type": koers_mapping[k]} for k in race_cols]))

with tab4:
    st.write("Live versie met optimalisatie algoritme.")
