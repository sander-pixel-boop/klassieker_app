import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS & News Master Sync", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd').replace('-', ' ')
    text = re.sub(r'[^a-z\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 Wieler-Updater: PCS vs Nieuws Check")

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
        # We slaan de huidige status op om te kunnen vergelijken (wie stond er al op 1?)
        oud_vinkjes = st.session_state['matrix'][race].copy()
        
        tekst_bak = deep_clean(plak_veld)
        herkende_namen = []
        
        # Stap 1: Nieuwe vinkjes zetten op basis van PCS
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            delen = schoon_naam.split()
            
            if len(delen) >= 2:
                voornaam = delen[0]
                achternaam = delen[-1]
                
                # Check op achternaam + voornaam (of initiaal)
                if achternaam in tekst_bak:
                    if voornaam in tekst_bak or (len(voornaam) > 0 and f" {voornaam[0]} " in f" {tekst_bak} "):
                        st.session_state['matrix'].at[naam, race] = 1
                        herkende_namen.append(naam)

        # Stap 2: Analyse van de verschillen
        st.success(f"Update voltooid! {len(herkende_namen)} renners herkend in de PDF.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Herkend door PCS")
            st.caption("Deze renners staan nu sowieso op 1.")
            st.write(", ".join(sorted(herkende_namen)))

        with col2:
            # Wie stond op 1 (nieuws), maar staat NIET in de PDF?
            niet_gevonden = [naam for naam in st.session_state['matrix'].index 
                             if oud_vinkjes[naam] == 1 and naam not in herkende_namen]
            
            st.subheader("⚠️ Niet in PDF (Nieuws-data)")
            if niet_gevonden:
                st.warning(f"Deze {len(niet_gevonden)} renners stonden in je nieuws-data maar NIET in de PCS PDF.")
                st.info("Check of ze zijn afgevallen of een andere spelling hebben.")
                st.write(", ".join(sorted(niet_gevonden)))
            else:
                st.success("Alle nieuws-vinkjes zijn bevestigd door de PDF!")

st.subheader("Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download", csv, "startlijsten.csv", "text/csv")
