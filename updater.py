import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="Strikte PCS Sync")

def clean_text(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

st.title("🔄 Strikte PCS Updater")
st.write("Deze versie filtert footer-renners eruit door alleen naar de tabelregels te kijken.")

# 1. Laden van de referentie (Altijd de basis)
try:
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except:
    st.error("Kan renners_stats.csv niet vinden. Zorg dat deze op GitHub staat.")
    st.stop()

# 2. Setup van de Matrix (Geen startlijsten.csv nodig als basis)
if 'matrix' not in st.session_state:
    # We maken altijd een nieuwe lege matrix op basis van de stats lijst
    st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
    st.session_state['matrix'].index.name = "Naam"

race = st.selectbox("Selecteer koers:", st.session_state['matrix'].columns)
plak_veld = st.text_area("Plak hier de PCS tekst (Ctrl+A):", height=300)

if st.button(f"Overschrijf {race}"):
    if plak_veld:
        # Stap A: Reset de kolom voor deze race
        st.session_state['matrix'][race] = 0
        
        # Stap B: Super-strikte filtering
        regels = plak_veld.split('\n')
        gevalideerde_tekst = ""
        
        for regel in regels:
            s_regel = regel.strip()
            # Een echte startlijst-regel begint bijna altijd met:
            # - Een getal (rugnummer)
            # - Streepjes '---'
            # - Of bevat specifieke ploeg-indicators die niet in de footer staan
            if re.match(r'^\d+', s_regel) or s_regel.startswith('---'):
                gevalideerde_tekst += " " + s_regel

        gevonden = 0
        data_schoon = clean_text(gevalideerde_tekst)
        
        # Stap C: Matching op achternaam
        for naam in master_names:
            parts = clean_text(naam).split()
            if not parts: continue
            achternaam = parts[-1]
            
            # We zoeken de achternaam in de gefilterde tekst
            if f" {achternaam}" in f" {data_schoon}":
                st.session_state['matrix'].at[naam, race] = 1
                gevonden += 1
        
        st.success(f"Gereed! {gevonden} renners gevonden in de tabel van {race}.")
        st.dataframe(st.session_state['matrix'][st.session_state['matrix'][race] == 1])

# 3. Export
st.divider()
if not st.session_state['matrix'].empty:
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download nieuwe startlijsten.csv", csv, "startlijsten.csv", "text/csv")
