import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS Master Sync - Hersteld", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    # We behouden hier even de nummers en punten omdat we regel-voor-regel checken
    return text.strip()

st.title("🔄 Wieler-Updater: Herstelde Match-Logica")

# 1. Laden van de data
if 'matrix' not in st.session_state:
    try:
        df_bron = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
        name_col = 'Naam' if 'Naam' in df_bron.columns else 'NAAM'
        st.session_state['matrix'] = df_bron.set_index(name_col)
        st.success("✅ bron_startlijsten.csv geladen.")
    except Exception as e:
        st.error("❌ bron_startlijsten.csv niet gevonden.")
        st.stop()

race = st.selectbox("Update koers:", st.session_state['matrix'].columns.tolist())
plak_veld = st.text_area("Plak hier de PCS PDF tekst:", height=250)

if st.button(f"Start Update {race}"):
    if plak_veld:
        # Sla oude status op voor de vergelijking
        oud_vinkjes = st.session_state['matrix'][race].copy()
        
        # Split de tekst in losse regels (zoals de PDF binnenkomt)
        regels = plak_veld.split('\n')
        schoon_regels = [deep_clean(r) for r in regels if r.strip()]
        
        herkende_namen = []
        
        # Stap 1: Match per regel (de succesvolle methode)
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            delen = schoon_naam.split()
            
            if len(delen) >= 2:
                # We pakken de belangrijkste delen: vaak de eerste en de laatste
                voornaam = delen[0]
                achternaam = delen[-1]
                
                # Check elke regel uit de PDF
                for regel in schoon_regels:
                    # De "Gouden Match": staan beide woorden in deze specifieke regel?
                    if achternaam in regel and voornaam in regel:
                        st.session_state['matrix'].at[naam, race] = 1
                        herkende_namen.append(naam)
                        break

        # Stap 2: Resultaten tonen
        st.success(f"Klaar! {len(herkende_namen)} renners herkend in de PDF.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Bevestigd door PCS")
            st.write(", ".join(sorted(herkende_namen)) if herkende_namen else "Geen matches.")

        with col2:
            # Wie stond op 1 (nieuws), maar staat NIET in de PDF?
            niet_gevonden = [naam for naam in st.session_state['matrix'].index 
                             if oud_vinkjes[naam] == 1 and naam not in herkende_namen]
            
            st.subheader("⚠️ Niet in PDF (Nieuws-data)")
            if niet_gevonden:
                st.warning(f"Deze {len(niet_gevonden)} renners stonden in je nieuws-data maar NIET in de PDF.")
                st.write(", ".join(sorted(niet_gevonden)))
            else:
                st.success("Alle nieuws-vinkjes zijn bevestigd!")

st.subheader("Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download", csv, "startlijsten.csv", "text/csv")
