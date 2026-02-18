import streamlit as st
import pandas as pd
import pulp

st.set_page_config(page_title="Klassiekers 2026 - Live", layout="wide")

def style_market(df, races):
    def color_coding(val):
        if val == "✅": return 'background-color: #d4edda; color: #155724;'
        if val == "❓": return 'background-color: #fff3cd; color: #856404;'
        return ''
    return df.style.applymap(color_coding, subset=races)

# 1. Data Laden
@st.cache_data
def load_all():
    df_wo = pd.read_csv("renners_stats.csv")
    df_sl = pd.read_csv("startlijsten.csv")
    df_wo.columns = [c.strip().upper() for c in df_wo.columns]
    df_sl.columns = [c.strip().upper() for c in df_sl.columns]
    
    merged = pd.merge(df_wo, df_sl, on="NAAM", how="left").fillna(0)
    merged['PRIJS_NUM'] = pd.to_numeric(merged['PRIJS'], errors='coerce').fillna(500000)
    return merged

df = load_all()
races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]

st.sidebar.title("Instellingen")
budget = st.sidebar.number_input("Budget (M)", value=48.0, step=0.5) * 1000000

# --- TABBLADEN ---
t1, t2 = st.tabs(["🏆 Team Optimalisatie", "📊 Transfermarkt"])

with t2:
    st.subheader("Volledige Markt")
    display_df = df.copy()
    for r in races:
        if r in display_df.columns:
            display_df[r] = display_df[r].map({1: "✅", 2: "❓", 0: ""}).fillna("")
    st.dataframe(style_market(display_df, races), height=600)

with t1:
    st.subheader("Beste Team op basis van jouw data")
    
    # PuLP Optimalisatie
    prob = pulp.LpProblem("ClassicTeam", pulp.LpMaximize)
    sel = pulp.LpVariable.dicts("rider", range(len(df)), cat='Binary')
    
    # Score berekening (simpel voorbeeld op COB + SPR)
    # Belangrijk: we tellen zowel 1 als 2 als starters
    total_score = pulp.lpSum([
        (df['COB'][i] + df['SPR'][i]) * sel[i] for i in range(len(df))
    ])
    prob += total_score
    
    # Constraints
    prob += pulp.lpSum([df['PRIJS_NUM'][i] * sel[i] for i in range(len(df))]) <= budget
    prob += pulp.lpSum([sel[i] for i in range(len(df))]) == 20
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] == 'Optimal':
        chosen_indices = [i for i in range(len(df)) if sel[i].varValue > 0]
        team_df = df.iloc[chosen_indices].copy()
        
        for r in races:
            team_df[r] = team_df[r].map({1: "✅", 2: "❓", 0: ""}).fillna("")
            
        st.write(f"**Totaal Budget Gebruikt:** {team_df['PRIJS_NUM'].sum():,.0f}")
        st.dataframe(style_market(team_df[['NAAM', 'PRIJS', 'COB', 'SPR'] + races], races))
    else:
        st.error("Kon geen optimaal team vinden met dit budget.")
