import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="Strikte Naam Matching")

def clean_text(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

st.title("🔄 PCS Startlijst Updater - Precisie Editie")
st.write("Deze versie voorkomt verwarring tussen renners met dezelfde achternaam (zoals de Pedersens).")

# 1. Laden van de referentie (WielerOrakel lijst)
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

race = st.selectbox("Kies koers:", st.session_state['matrix'].columns)
plak_veld = st.text_area("Plak hier de PCS tekst (Printable/PDF versie):", height=300)

if st.button(f"Update {race}"):
    if plak_veld:
        st.session_state['matrix'][race] = 0
        
        # Filteren op regels die beginnen met een rugnummer
        regels = plak_veld.split('\n')
        gevalideerde_regels = [clean_text(r) for r in regels if re.match(r'^\d+', r.strip())]

        gevonden = 0
        
        for naam in master_names:
            schoon_naam = clean_text(naam)
            naam_delen = schoon_naam.split()
            
            if len(naam_delen) >= 2:
                voornaam = naam_delen[0]
                achternaam = naam_delen[-1]
                
                # Check elke gevalideerde regel uit de startlijst
                for regel in gevalideerde_regels:
                    # De renner krijgt alleen een vinkje als EN de voornaam EN de achternaam in de regel staan
                    if achternaam in regel and voornaam in regel:
                        st.session_state['matrix'].at[naam, race] = 1
                        gevonden += 1
                        break # Stop met zoeken voor deze renner in deze koers

        st.success(f"Gereed! {gevonden} renners uniek geïdentificeerd voor {race}.")
        
        # Toon preview van de vinkjes
        check_df = st.session_state['matrix'][st.session_state['matrix'][race] == 1]
        st.dataframe(check_df[[race]])

# 3. Export
st.divider()
if st.button("Download startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Bestand Opslaan", csv, "startlijsten.csv", "text/csv")
