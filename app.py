import streamlit as st
import pandas as pd
import pulp

st.set_page_config(page_title="Scorito Klassiekers")
st.title("🚴 Scorito Team Optimalisatie")

# 1. INPUTS
st.sidebar.header("Instellingen")
budget = st.sidebar.number_input("Budget", value=46000000, step=250000)
aantal_renners = st.sidebar.number_input("Aantal renners", value=20)

st.write("### Stap 1: Upload je data")
st.write("Zorg dat je Excel/CSV kolommen heeft: `Naam`, `Prijs`, `Punten`")
uploaded_file = st.file_uploader("Kies je bestand", type=["csv", "xlsx"])

if uploaded_file:
    # Lees bestand (automatisch csv of excel detectie)
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Check of kolommen bestaan
    required_cols = ['Naam', 'Prijs', 'Punten']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Je bestand mist kolommen. Zorg voor: {required_cols}")
    else:
        st.success(f"{len(df)} renners geladen.")
        
        # 2. HET ALGORITME (Knapsack Problem)
        if st.button("🚀 Genereer Beste Team"):
            problem = pulp.LpProblem("ScoritoTeam", pulp.LpMaximize)
            
            # Maak een variabele voor elke renner (0 = niet kiezen, 1 = wel kiezen)
            selection = pulp.LpVariable.dicts("Select", df.index, cat='Binary')
            
            # Doel: Maximaliseer totaal punten
            problem += pulp.lpSum([df['Punten'][i] * selection[i] for i in df.index])
            
            # Beperking 1: Budget
            problem += pulp.lpSum([df['Prijs'][i] * selection[i] for i in df.index]) <= budget
            
            # Beperking 2: Aantal renners
            problem += pulp.lpSum([selection[i] for i in df.index]) == aantal_renners
            
            # Los op
            problem.solve()
            
            # 3. RESULTAAT
            if pulp.LpStatus[problem.status] == 'Optimal':
                selected_indices = [i for i in df.index if selection[i].varValue == 1]
                team = df.loc[selected_indices]
                
                st.write("### 🏆 Het Optimale Team")
                st.dataframe(team[['Naam', 'Prijs', 'Punten']])
                
                totaal_prijs = team['Prijs'].sum()
                totaal_punten = team['Punten'].sum()
                
                col1, col2 = st.columns(2)
                col1.metric("Totaal Kosten", f"€ {totaal_prijs:,}")
                col2.metric("Verwachte Punten", f"{totaal_punten:.0f}")
                
                if totaal_prijs > budget:
                    st.error("Let op: Budget overschreden (zou niet mogen gebeuren).")
            else:
                st.error("Geen oplossing gevonden binnen de regels.")
