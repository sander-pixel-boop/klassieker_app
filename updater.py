import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Data Sync Tool")

def clean_text(text):
    if not text: return ""
    text = str(text).lower()
    # Verwijder accenten voor betere matching
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

st.title("🔄 Renners & Startlijst Updater")
st.write("Kopieer de volledige pagina van een PCS startlijst (Ctrl+A) en plak deze hieronder.")

# 1. Laden van de referentie (WielerOrakel lijst)
try:
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except:
    st.error("Kan renners_stats.csv niet vinden op GitHub.")
    st.stop()

# 2. Selectie van de koers
race = st.selectbox("Selecteer de koers:", ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])

# 3. Het plakveld
plak_veld = st.text_area("Plak hier de PCS tekst:", height=300)

# Initialiseer de matrix in de sessie als die nog niet bestaat
if 'matrix' not in st.session_state:
    # Probeer de bestaande startlijsten te laden, anders maak een nieuwe
    try:
        st.session_state['matrix'] = pd.read_csv("startlijsten.csv", index_col='Naam')
    except:
        st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
        st.session_state['matrix'].index.name = "Naam"

if st.button("Verwerk Gegevens"):
    if plak_veld:
        gevonden = 0
        data_schoon = clean_text(plak_veld)
        
        for naam in master_names:
            # We zoeken op de achternaam om kleine verschillen in voorletters op te vangen
            achternaam = clean_text(naam).split()[-1]
            if achternaam in data_schoon:
                st.session_state['matrix'].at[naam, race] = 1
                gevonden += 1
        
        st.success(f"Klaar! {gevonden} renners uit WielerOrakel herkend in deze lijst.")
        st.dataframe(st.session_state['matrix'])

# 4. Export
if st.button("Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download Bestand", csv, "startlijsten.csv", "text/csv")
