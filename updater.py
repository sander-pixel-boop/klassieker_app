import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS Master Sync - Final Fix", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd').replace('-', ' ')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 Wieler-Updater: Volgorde-Vrije Match")
st.info("Deze versie herkent renners ongeacht of de achternaam of voornaam eerst staat.")

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
plak_veld = st.text_area("Plak hier de PCS tekst:", height=250)

if st.button(f"Start Update {race}"):
    if plak_veld:
        oud_vinkjes = st.session_state['matrix'][race].copy()
        
        # We maken één grote bak met schoongemaakte tekst van de PDF
        tekst_bak = deep_clean(plak_veld)
        
        herkende_namen = []
        
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            # We filteren stopwoorden eruit en houden alleen echte namen over
            stopwoorden = {'van', 'den', 'der', 'de', 'het', 'ten', 'ter'}
            naam_delen = [d for d in schoon_naam.split() if d not in stopwoorden and len(d) > 2]
            
            if naam_delen:
                # MATCH LOGICA: Alle belangrijke delen van de naam (bijv. 'jasper' en 'philipsen')
                # moeten ergens in de tekst voorkomen. De volgorde maakt niet uit.
                if all(deel in tekst_bak for deel in naam_delen):
                    st.session_state['matrix'].at[naam, race] = 1
                    herkende_namen.append(naam)

        # Statistieken tonen
        totaal_deelnemers = (st.session_state['matrix'][race] == 1).sum()
        
        st.metric(label=f"Totaal aantal renners met vinkje voor {race}", value=totaal_deelnemers)
        st.success(f"Er zijn {len(herkende_namen)} renners uit de PDF bevestigd.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 Bevestigd door PCS")
            st.write(", ".join(sorted(herkende_namen)))

        with col2:
            niet_gevonden = [n for n in st.session_state['matrix'].index 
                             if oud_vinkjes[n] == 1 and n not in herkende_namen]
            st.subheader("⚠️ Alleen in Nieuws-data")
            if niet_gevonden:
                st.warning(f"{len(niet_gevonden)} renners niet gevonden in PDF.")
                st.write(", ".join(sorted(niet_gevonden)))

st.subheader("Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download", csv, "startlijsten.csv", "text/csv")
