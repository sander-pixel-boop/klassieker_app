import streamlit as st
import pandas as pd
import pulp
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Scorito & Startlijsten", layout="wide")
st.title("🚴 Scorito Team & Startlijsten Check")

# --- FUNCTIE: STARTLIJSTEN SCRAPEN ---
@st.cache_data(ttl=3600) # Bewaar data 1 uur zodat je niet steeds opnieuw hoeft te laden
def get_startlists():
    # De belangrijkste klassiekers (URLs voor 2026)
    races = {
        "Omloop": "https://www.procyclingstats.com/race/omloop-het-nieuwsblad/2026/startlist",
        "Kuurne": "https://www.procyclingstats.com/race/kuurne-brussel-kuurne/2026/startlist",
        "Strade": "https://www.procyclingstats.com/race/strade-bianche/2026/startlist",
        "Sanremo": "https://www.procyclingstats.com/race/milano-sanremo/2026/startlist",
        "E3 Saxo": "https://www.procyclingstats.com/race/e3-harelbeke/2026/startlist",
        "Gent-Wevelgem": "https://www.procyclingstats.com/race/gent-wevelgem/2026/startlist",
        "Dwars v Vl": "https://www.procyclingstats.com/race/dwars-door-vlaanderen/2026/startlist",
        "Vlaanderen": "https://www.procyclingstats.com/race/ronde-van-vlaanderen/2026/startlist",
        "Roubaix": "https://www.procyclingstats.com/race/paris-roubaix/2026/startlist",
        "Brabantse Pijl": "https://www.procyclingstats.com/race/brabantse-pijl/2026/startlist",
        "Amstel Gold": "https://www.procyclingstats.com/race/amstel-gold-race/2026/startlist",
        "Waalse Pijl": "https://www.procyclingstats.com/race/fleche-wallonne/2026/startlist",
        "Luik": "https://www.procyclingstats.com/race/liege-bastogne-liege/2026/startlist",
        "Eschborn": "https://www.procyclingstats.com/race/eschborn-frankfurt/2026/startlist"
    }
    
    startlist_data = {} # Hier slaan we op wie wat rijdt
    
    progress_bar = st.progress(0)
    status = st.empty()
    
    i = 0
    for race, url in races.items():
        status.text(f"Checken startlijst: {race}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Zoek alle renners op de pagina
            riders = soup.select('a[href^="rider/"]')
            
            for r in riders:
                name = r.text.strip().lower() # Alles kleine letters voor makkelijkere match
                if name not in startlist_data:
                    startlist_data[name] = []
                if race not in startlist_data[name]:
                    startlist_data[name].append(race)
                    
        except Exception as e:
            print(f"Fout bij {race}: {e}")
            
        i += 1
        progress_bar.progress(i / len(races))
        time.sleep(0.3) # Kleine pauze
        
    status.text("Alle startlijsten binnen!")
    progress_bar.empty()
    return startlist_data

# --- SIDEBAR ---
budget = st.sidebar.number_input("Budget (€)", value=46000000, step=250000)
st.sidebar.info("Upload Scorito CSV (Kolommen: Naam, Prijs, Waarde)")
uploaded_file = st.sidebar.file_uploader("Upload Scorito Bestand", type=["csv", "xlsx"])

# --- HOOFDLOGICA ---
col1, col2 = st.columns([1, 2])

with col1:
    st.write("### Stap 1: Check Startlijsten")
    if st.button("Update Startlijsten (Live PCS)"):
        st.session_state['startlists'] = get_startlists()
        st.success("Startlijsten geladen!")

    # Toon statistiek als data er is
    if 'startlists' in st.session_state:
        st.write(f"Renners in database: {len(st.session_state['startlists'])}")

with col2:
    if uploaded_file and 'startlists' in st.session_state:
        # 1. Inlezen Scorito bestand
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)
            
        # Kolommen schoonmaken
        df.columns = df.columns.str.strip()
        df['Prijs_Clean'] = df['Prijs'].astype(str).str.replace('€', '').str.replace('.', '').str.replace(' ', '')
        df['Prijs_Clean'] = pd.to_numeric(df['Prijs_Clean'], errors='coerce').fillna(0)
        df['Waarde_Clean'] = pd.to_numeric(df['Waarde'], errors='coerce').fillna(0)
        
        # 2. MATCHEN MET STARTLIJSTEN
        pcs_data = st.session_state['startlists']
        
        programmas = []
        aantal_races = []
        
        for index, row in df.iterrows():
            # Naam uit Excel
            naam_scorito = str(row['Naam']).lower().strip()
            
            # Check of hij in de PCS lijst staat
            # (Simpele check: staat de achternaam in de string?)
            found_races = []
            
            # Exacte match proberen
            if naam_scorito in pcs_data:
                found_races = pcs_data[naam_scorito]
            else:
                # Fallback: Soms is het "M. van der Poel" vs "Mathieu van der Poel"
                # We zoeken in PCS sleutels of de scorito naam er deels in zit
                for pcs_name in pcs_data:
                    if naam_scorito in pcs_name or pcs_name in naam_scorito:
                        found_races = pcs_data[pcs_name]
                        break
            
            programmas.append(", ".join(found_races))
            aantal_races.append(len(found_races))
            
        df['Races'] = programmas
        df['Aantal_Startlijsten'] = aantal_races
        
        # Toon tabel met extra info
        st.write("### Jouw Renners & Hun Programma")
        st.dataframe(df[['Naam', 'Prijs', 'Waarde', 'Aantal_Startlijsten', 'Races']].sort_values('Aantal_Startlijsten', ascending=False))
        
        # 3. OPTIMALISATIE
        st.write("### Stap 2: Optimaliseer Team")
        st.info("Tip: De optimalisatie kiest nu renners met de hoogste 'Waarde' die binnen budget passen.")
        
        if st.button("Kies Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
            
            # Doel: Waarde maximaliseren
            prob += pulp.lpSum([df['Waarde_Clean'][i] * sel[i] for i in df.index])
            # Budget
            prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
            # Aantal
            prob += pulp.lpSum([sel[i] for i in df.index]) == 20
            
            prob.solve()
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                idx = [i for i in df.index if sel[i].varValue == 1]
                team = df.loc[idx]
                st.success(f"Team gevonden! Kosten: € {team['Prijs_Clean'].sum():,.0f}")
                st.dataframe(team[['Naam', 'Prijs', 'Aantal_Startlijsten', 'Races']])
            else:
                st.error("Geen team gevonden.")

    elif not uploaded_file:
        st.warning("Upload eerst je bestand.")
    elif 'startlists' not in st.session_state:
        st.warning("Klik eerst op 'Update Startlijsten'.")
