import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS Master Sync - Restore", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Belangrijk: Deense ø en andere varianten platstaan
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd').replace('-', ' ')
    text = re.sub(r'[^a-z\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 Wieler-Updater: Herstelde Match-Logica")
st.info("Deze versie geeft prioriteit aan de achternaam om het hoge aantal matches (165+) terug te krijgen.")

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
        # We maken één grote tekstbak van de PDF
        tekst_bak = deep_clean(plak_veld)
        herkende_namen = []
        
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            delen = schoon_naam.split()
            
            if len(delen) >= 2:
                voornaam = delen[0]
                achternaam = delen[-1]
                
                # LOGICA: We zoeken eerst de achternaam. 
                # Als die er is, checken we of de voornaam (of de eerste letter) er ook is.
                if achternaam in tekst_bak:
                    # Check voor volledige voornaam OF eerste letter van de voornaam (bijv. 'k' voor 'kasper')
                    if voornaam in tekst_bak or (len(voornaam) > 0 and f" {voornaam[0]} " in f" {tekst_bak} "):
                        st.session_state['matrix'].at[naam, race] = 1
                        herkende_namen.append(naam)

        st.success(f"Klaar! {len(herkende_namen)} renners herkend voor {race}.")
        with st.expander("Bekijk de lijst van herkende renners"):
            st.write(", ".join(sorted(herkende_namen)))

st.subheader("Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download", csv, "startlijsten.csv", "text/csv")
