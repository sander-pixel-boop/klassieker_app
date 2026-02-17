import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Scorito & Programma", layout="wide")
st.title("🚴 Scorito Team & Programma Matrix")

# --- 1. CONFIGURATIE & SCRAPER ---
RACES = {
    "Omloop": "https://www.procyclingstats.com/race/omloop-het-nieuwsblad/2026/startlist",
    "Kuurne": "https://www.procyclingstats.com/race/kuurne-brussel-kuurne/2026/startlist",
    "Strade": "https://www.procyclingstats.com/race/strade-bianche/2026/startlist",
    "Sanremo": "https://www.procyclingstats.com/race/milano-sanremo/2026/startlist",
    "E3": "https://www.procyclingstats.com/race/e3-harelbeke/2026/startlist",
    "Gent-W": "https://www.procyclingstats.com/race/gent-wevelgem/2026/startlist",
    "DDV": "https://www.procyclingstats.com/race/dwars-door-vlaanderen/2026/startlist",
    "Vlaanderen": "https://www.procyclingstats.com/race/ronde-van-vlaanderen/2026/startlist",
    "Scheldeprijs": "https://www.procyclingstats.com/race/scheldeprijs/2026/startlist",
    "Roubaix": "https://www.procyclingstats.com/race/paris-roubaix/2026/startlist",
    "Brabantse": "https://www.procyclingstats.com/race/brabantse-pijl/2026/startlist",
    "Amstel": "https://www.procyclingstats.com/race/amstel-gold-race/2026/startlist",
    "Waalse Pijl": "https://www.procyclingstats.com/race/fleche-wallonne/2026/startlist",
    "Luik": "https://www.procyclingstats.com/race/liege-bastogne-liege/2026/startlist",
    "Eschborn": "https://www.procyclingstats.com/race/eschborn-frankfurt/2026/startlist"
}

@st.cache_data(ttl=3600)
def get_startlists():
    data = {}
    progress = st.progress(0)
    status = st.empty()
    
    i = 0
    for race_name, url in RACES.items():
        status.text(f"Ophalen: {race_name}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.content, 'html.parser')
            riders = soup.select('a[href^="rider/"]')
            
            for r in riders:
                name = r.text.strip().lower()
                if name not in data:
                    data[name] = []
                if race_name not in data[name]:
                    data[name].append(race_name)
        except Exception as e:
            print(f"Error {race_name}: {e}")
        
        i += 1
        progress.progress(i / len(RACES))
        time.sleep(0.2)
    
    status.empty()
    progress.empty()
    return data

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    budget = st.number_input("Budget (€)", value=46000000, step=250000)
    st.info("Upload een CSV met: Naam, Prijs, Waarde")
    uploaded_file = st.file_uploader("Upload Bestand", type=["csv", "xlsx"])
    
    st.divider()
    if st.button("🔄 Ververs Startlijsten (PCS)"):
        st.session_state['startlists'] = get_startlists()
        st.success("Geüpdatet!")

# --- 3. HOOFDSCHERM ---
if 'startlists' not in st.session_state:
    st.warning("Klik eerst links op 'Ververs Startlijsten' om de data van PCS te halen.")
elif not uploaded_file:
    st.info("👈 Upload je Scorito-bestand in de zijbalk om te beginnen.")
else:
    # A. Data Inladen
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
    else:
        df = pd.read_excel(uploaded_file)
        
    # Schoonmaak
    df.columns = df.columns.str.strip()
    df['Prijs_Clean'] = df['Prijs'].astype(str).str.replace('€', '').str.replace('.', '').str.replace(' ', '')
    df['Prijs_Clean'] = pd.to_numeric(df['Prijs_Clean'], errors='coerce').fillna(0)
    df['Waarde_Clean'] = pd.to_numeric(df['Waarde'], errors='coerce').fillna(0)

    # B. Koppelen aan PCS
    pcs = st.session_state['startlists']
    programma_count = []
    
    # Voor elke renner kijken welke races hij rijdt
    for idx, row in df.iterrows():
        name = str(row['Naam']).lower().strip()
        races_found = []
        
        # 1. Exacte match
        if name in pcs:
            races_found = pcs[name]
        else:
            # 2. Gedeeltelijke match (voor "M. van der Poel" vs "Mathieu...")
            for pcs_name in pcs:
                if name in pcs_name or pcs_name in name:
                    races_found = pcs[pcs_name]
                    break
        
        programma_count.append(len(races_found))
        # We slaan de lijst races op in een verborgen kolom voor later gebruik
        df.at[idx, 'Races_List'] = ",".join(races_found)

    df['Aantal_Races'] = programma_count

    st.write(f"### 📊 Gevonden renners: {len(df)}")
    
    # C. Optimalisatie
    if st.button("🚀 Genereer Optimaal Team"):
        prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
        sel = pulp.LpVariable.dicts("Select", df.index, cat='Binary')
        
        # Doel: Max Waarde
        prob += pulp.lpSum([df['Waarde_Clean'][i] * sel[i] for i in df.index])
        # Constraint: Budget
        prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
        # Constraint: 20 Renners
        prob += pulp.lpSum([sel[i] for i in df.index]) == 20
        
        prob.solve()
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            idx = [i for i in df.index if sel[i].varValue == 1]
            team = df.loc[idx].copy()
            
            # --- D. HET SCHEMA MAKEN ---
            st.success(f"Team compleet! Kosten: € {team['Prijs_Clean'].sum():,.0f}")
            
            # Maak de matrix
            schedule_data = []
            race_columns = list(RACES.keys())
            
            for i, row in team.iterrows():
                rider_schedule = {"Renner": row['Naam'], "Prijs": row['Prijs'], "Waarde": row['Waarde']}
                
                # Haal races op die we eerder vonden
                my_races = str(row['Races_List']).split(',')
                
                for race in race_columns:
                    if race in my_races:
                        rider_schedule[race] = "✅"
                    else:
                        rider_schedule[race] = "" # Leeg laten of ❌
                
                schedule_data.append(rider_schedule)
            
            df_schedule = pd.DataFrame(schedule_data)
            
            # Weergave
            st.write("### 📅 Wedstrijdschema")
            st.dataframe(
                df_schedule.set_index("Renner"), 
                height=800,
                column_config={
                    "Prijs": st.column_config.TextColumn("Prijs"),
                }
            )
            
        else:
            st.error("Kon geen team maken binnen dit budget.")
