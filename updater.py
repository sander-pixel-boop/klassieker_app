import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PDF Startlijst Sync")

def clean_text(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

st.title("🔄 PCS PDF/Print Updater")
st.write("Ga op PCS naar de startlijst, klik op **'Print'** of **'PDF'**, kopieer alle tekst (Ctrl+A) en plak deze hieronder.")

# 1. Laden van de referentie (Stats lijst)
try:
    # We laden stats.csv als de masterlijst
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except:
    st.error("Kan renners_stats.csv niet vinden op GitHub.")
    st.stop()

# 2. Setup Matrix
if 'matrix' not in st.session_state:
    st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
    st.session_state['matrix'].index.name = "Naam"

race = st.selectbox("Selecteer koers:", st.session_state['matrix'].columns)
plak_veld = st.text_area("Plak hier de PDF/Print tekst:", height=300)

if st.button(f"Update {race}"):
    if plak_veld:
        # Stap A: Reset de kolom
        st.session_state['matrix'][race] = 0
        
        # Stap B: Filteren op PDF-structuur
        # PDF-lijsten hebben vaak de structuur: "1 Pogačar Tadej" of "1. Pogačar Tadej"
        regels = plak_veld.split('\n')
        gevalideerde_tekst = ""
        
        for regel in regels:
            s_regel = regel.strip()
            # We zoeken regels die beginnen met een nummer (rugnummer)
            if re.match(r'^\d+', s_regel):
                gevalideerde_tekst += " " + s_regel

        gevonden = 0
        data_schoon = clean_text(gevalideerde_tekst)
        
        # Stap C: Matching
        for naam in master_names:
            parts = clean_text(naam).split()
            if not parts: continue
            # Gebruik de achternaam voor de match
            achternaam = parts[-1]
            
            # Check of de achternaam in de gefilterde regels voorkomt
            if achternaam and achternaam in data_schoon:
                st.session_state['matrix'].at[naam, race] = 1
                gevonden += 1
        
        st.success(f"Gereed! {gevonden} renners uit je database herkend voor {race}.")
        
        # Toon alleen de herkende renners als controle
        check_df = st.session_state['matrix'][st.session_state['matrix'][race] == 1]
        st.dataframe(check_df[[race]])

# 3. Export
st.divider()
if st.button("Download nieuwe startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Klik om te downloaden", csv, "startlijsten.csv", "text/csv")
