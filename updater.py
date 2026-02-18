import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS Master Sync", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    return text.strip()

st.title("🔄 Wieler-Updater: PCS vs Nieuws")

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
        # Sla oude status op om te zien wie er al op 1 stond
        oud_vinkjes = st.session_state['matrix'][race].copy()
        
        # We maken de tekstbak schoon maar behouden de regels
        regels = plak_veld.split('\n')
        schoon_regels = [deep_clean(r) for r in regels if r.strip()]
        volledige_tekst = " ".join(schoon_regels)
        
        herkende_namen = []
        
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            delen = schoon_naam.split()
            
            if len(delen) >= 2:
                voornaam = delen[0]
                achternaam = delen[-1]
                
                # We zoeken de achternaam in de tekst
                if achternaam in volledige_tekst:
                    # Als de voornaam of de eerste letter van de voornaam ook in de tekst staat: MATCH
                    if voornaam in volledige_tekst or (len(voornaam) > 0 and voornaam[0] in volledige_tekst):
                        st.session_state['matrix'].at[naam, race] = 1
                        herkende_namen.append(naam)

        # Statistieken
        totaal_deelnemers = (st.session_state['matrix'][race] == 1).sum()
        
        st.metric(label=f"Totaal aantal renners voor {race}", value=totaal_deelnemers)
        st.success(f"Er zijn {len(herkende_namen)} matches gevonden in de PDF.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 Bevestigd door PCS")
            st.write(", ".join(sorted(herkende_namen)))

        with col2:
            niet_gevonden = [naam for naam in st.session_state['matrix'].index 
                             if oud_vinkjes[naam] == 1 and naam not in herkende_namen]
            st.subheader("⚠️ Niet in PDF (Nieuws-data)")
            if niet_gevonden:
                st.warning(f"Deze {len(niet_gevonden)} renners stonden op 1 maar zijn niet gevonden.")
                st.write(", ".join(sorted(niet_gevonden)))

st.subheader("Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download", csv, "startlijsten.csv", "text/csv")
