import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS Startlijst Sync - Full Overwrite")

def clean_text(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

st.title("🔄 PCS Startlijst Updater")
st.write("Deze versie verwijdert automatisch renners die niet meer op de lijst staan.")

# 1. Laden van de referentie (WielerOrakel lijst)
try:
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except:
    st.error("Kan renners_stats.csv niet vinden. Zorg dat dit bestand op GitHub staat.")
    st.stop()

race = st.selectbox("Selecteer de koers om te updaten:", ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
plak_veld = st.text_area("Plak hier de volledige PCS pagina (Ctrl+A):", height=300)

# Initialiseer of laad de matrix
if 'matrix' not in st.session_state:
    try:
        st.session_state['matrix'] = pd.read_csv("startlijsten.csv", index_col='Naam')
    except:
        st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
        st.session_state['matrix'].index.name = "Naam"

if st.button(f"Update {race} (Overschrijf vorige lijst)"):
    if plak_veld:
        # --- STAP A: RESET --- 
        # We zetten de hele kolom voor deze specifieke race op 0.
        # Oude renners die niet meer in de nieuwe plak-tekst staan, vallen hierdoor af.
        st.session_state['matrix'][race] = 0
        
        # --- STAP B: FILTER ---
        regels = plak_veld.split('\n')
        gefilterde_tekst = ""
        for regel in regels:
            # Alleen regels met rugnummers of '---' (negeert footer/zijbalk)
            if re.search(r'\b\d{1,3}\b', regel) or "---" in regel:
                gefilterde_tekst += " " + regel

        gevonden = 0
        data_schoon = clean_text(gefilterde_tekst)
        
        # --- STAP C: MATCHING ---
        for naam in master_names:
            achternaam = clean_text(naam).split()[-1]
            if achternaam and achternaam in data_schoon:
                st.session_state['matrix'].at[naam, race] = 1
                gevonden += 1
        
        st.success(f"Update voltooid voor {race}!")
        st.info(f"Totaal {gevonden} renners op de nieuwe lijst. Vorige data voor deze koers is gewist.")
        st.dataframe(st.session_state['matrix'])

# 4. Export naar CSV
st.divider()
if st.button("Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download Bestand", csv, "startlijsten.csv", "text/csv")
