import streamlit as st
import pandas as pd
import pulp
import os  # Cruciaal voor het controleren van bestanden!

st.set_page_config(page_title="Klassieker Optimizer 2026", layout="wide")

# Styling voor de tabel
def style_df(df, races):
    return df.style.applymap(lambda x: 'background-color: #d4edda;' if x == 1 else '', subset=races)

@st.cache_data
def get_data():
    # 1. WielerOrakel Stats laden
    df_wo = pd.read_csv("renners_stats.csv")
    df_wo.columns = [c.strip().upper() for c in df_wo.columns]
    
    # Zoek de naamkolom (NAAM of NAAM_RENNER etc)
    name_col = 'NAAM' if 'NAAM' in df_wo.columns else df_wo.columns[0]
    
    # 2. Startlijsten laden (gegenereerd door updater)
    if os.path.exists("startlijsten.csv"):
        df_sl = pd.read_csv("startlijsten.csv")
        df_sl.columns = [c.strip().upper() for c in df_sl.columns]
        # Merge op naam
        merged = pd.merge(df_wo, df_sl, on=name_col, how="left").fillna(0)
    else:
        # Fallback als er nog geen startlijst is
        merged = df_wo.copy()
        for r in ["OHN","KBK","SB"]: merged[r] = 0
        
    merged['PRIJS_NUM'] = pd.to_numeric(merged['PRIJS'], errors='coerce').fillna(500000)
    return merged, name_col

df, NAME_COL = get_data()
races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
# Alleen kolommen gebruiken die echt in de data zitten
races_present = [r for r in races if r in df.columns]

st.title("🏆 Klassieker Team Optimizer")

# --- SIDEBAR ---
st.sidebar.header("Parameters")
budget = st.sidebar.slider("Totaal Budget (M)", 40.0, 60.0, 48.0) * 1000000
min_starts = st.sidebar.number_input("Minimaal aantal starts per renner", 0, 5, 1)

# --- OPTIMALISATIE ---
if st.button("Bereken Ideaal Team"):
    prob = pulp.LpProblem("ClassicTeam", pulp.LpMaximize)
    riders = range(len(df))
    select = pulp.LpVariable.dicts("select", riders, cat='Binary')

    # Doel: Maximaal potentieel (COB + SPR)
    prob += pulp.lpSum([(df['COB'][i] + df['SPR'][i]) * select[i] for i in riders])

    # Constraints
    prob += pulp.lpSum([df['PRIJS_NUM'][i] * select[i] for i in riders]) <= budget
    prob += pulp.lpSum([select[i] for i in riders]) == 20
    
    for i in riders:
        if sum(df[r][i] for r in races_present) < min_starts:
            prob += select[i] == 0

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] == 'Optimal':
        final_team = df.iloc[[i for i in riders if select[i].varValue > 0]]
        st.success(f"Team gevonden! Potentieel: {pulp.value(prob.objective):.0f}")
        st.dataframe(style_df(final_team[[NAME_COL, 'PRIJS', 'COB', 'SPR'] + races_present], races_present))
    else:
        st.error("Geen team mogelijk met deze filters.")

st.divider()
st.subheader("📊 De Volledige Markt")
st.dataframe(style_df(df[[NAME_COL, 'PRIJS', 'COB', 'SPR'] + races_present], races_present))
