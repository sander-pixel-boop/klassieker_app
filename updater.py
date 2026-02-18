import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS PDF Master Sync", layout="wide")

def clean_text(text):
    if not text: return ""
    text = str(text).lower()
    # Verwijder accenten
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Verwijder punten en speciale tekens
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text.strip()

st.title("🔄 PCS PDF/Print Updater - Verbeterde Herkenning")
st.write("Plak de tekst uit de PDF hieronder. Deze versie pakt ook namen met punten (11.) en complexe achternamen.")

# 1. Laden van de referentie (Stats lijst)
try:
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except:
    st.error("Kan renners_stats.csv niet vinden.")
    st.stop()

# 2. Setup Matrix
if 'matrix' not in st.session_state:
    st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
    st.session_state['matrix'].index.name = "Naam"

race = st.selectbox("Selecteer koers:", st.session_state['matrix'].columns)
plak_veld = st.text_area("Plak hier de PDF tekst:", height=300)

if st.button(f"Update {race}"):
    if plak_veld:
        st.session_state['matrix'][race] = 0
        regels = plak_veld.split('\n')
        
        # Stap A: Extraheer alleen de regels die met een nummer beginnen (ook 11. of 0.)
        gevalideerde_regels = []
        for r in regels:
            s_regel = r.strip()
            # Zoek naar regels die beginnen met een getal, gevolgd door optioneel een punt
            if re.match(r'^\d+', s_regel):
                gevalideerde_regels.append(clean_text(s_regel))

        gevonden = 0
        herkende_namen = []
        
        # Stap B: Matching
        for naam in master_names:
            schoon_naam = clean_text(naam)
            naam_delen = schoon_naam.split()
            
            if len(naam_delen) >= 2:
                # We checken of ALLE delen van de naam in de regel voorkomen (voornaam + achternaam)
                for regel in gevalideerde_regels:
                    # Match als elk deel van de naam in de regel staat
                    if all(deel in regel for deel in naam_delen):
                        st.session_state['matrix'].at[naam, race] = 1
                        gevonden += 1
                        herkende_namen.append(naam)
                        break

        st.success(f"Gereed! {gevonden} renners uniek geïdentificeerd voor {race}.")
        
        # Toon de lijst met herkende renners
        if herkende_namen:
            st.write("**Herkend:** " + ", ".join(herkende_namen))

# 3. Export
st.divider()
if st.button("Download nieuwe startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Klik om te downloaden", csv, "startlijsten.csv", "text/csv")
