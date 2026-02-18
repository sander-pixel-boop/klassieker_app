import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS & News Master Sync", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 Wieler-Updater: Nieuws + PCS")

# 1. Laden van de data uit de BRON
if 'matrix' not in st.session_state:
    try:
        df_bron = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
        name_col = 'Naam' if 'Naam' in df_bron.columns else 'NAAM'
        st.session_state['matrix'] = df_bron.set_index(name_col)
        st.success(f"✅ Basis geladen uit 'bron_startlijsten.csv'")
    except Exception as e:
        st.error(f"❌ Kan 'bron_startlijsten.csv' niet vinden.")
        st.stop()

race = st.selectbox("Welke koers updaten?", st.session_state['matrix'].columns.tolist())

plak_veld = st.text_area("Plak hier de PCS PDF tekst:", height=250)

if st.button(f"Update {race}"):
    if plak_veld:
        # We maken een grote 'bak' met schoongemaakte tekst van de hele PDF
        volledige_tekst_schoon = deep_clean(plak_veld)
        
        herkende_namen = []
        
        # We lopen door de database
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            naam_delen = [d for d in schoon_naam.split() if len(d) > 2] # Alleen belangrijke namen
            
            if naam_delen:
                # MATCH LOGICA: Alle belangrijke delen van de naam moeten in de PDF tekst staan
                if all(deel in volledige_tekst_schoon for deel in naam_delen):
                    st.session_state['matrix'].at[naam, race] = 1
                    herkende_namen.append(naam)

        st.success(f"Klaar! Er staan nu {len(herkende_namen)} renners op de lijst voor {race} (Nieuws + PCS).")
        
        # Controle op missers (optioneel)
        with st.expander("Bekijk de lijst van herkende renners"):
            st.write(", ".join(herkende_namen))

st.subheader("Huidige Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    final_csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download startlijsten.csv", final_csv, "startlijsten.csv", "text/csv")
