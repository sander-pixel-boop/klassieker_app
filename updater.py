import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS PDF Master Sync", layout="wide")

def deep_clean(text):
    if not text: return ""
    # Omzetten naar kleine letters
    text = str(text).lower()
    # Accenten en speciale tekens zoals ø verwijderen
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # De Deense ø wordt soms niet door NFD gepakt, dus handmatig:
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    # Alleen letters en cijfers overhouden
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 PCS PDF Master Updater - Accenten Fix")
st.write("Deze versie herkent ook Søren, Frølich, Søjberg en namen met koppeltekens.")

try:
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except:
    st.error("Kan renners_stats.csv niet vinden.")
    st.stop()

if 'matrix' not in st.session_state:
    st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
    st.session_state['matrix'].index.name = "Naam"

race = st.selectbox("Selecteer koers:", st.session_state['matrix'].columns)
plak_veld = st.text_area("Plak hier de PDF tekst:", height=300)

if st.button(f"Update {race}"):
    if plak_veld:
        st.session_state['matrix'][race] = 0
        regels = plak_veld.split('\n')
        
        # Stap A: Filter op regels met nummers
        gevalideerde_regels = []
        for r in regels:
            if re.search(r'\d+', r):
                gevalideerde_regels.append(deep_clean(r))

        gevonden = 0
        herkende_namen = []
        
        # Stap B: Matching
        for naam in master_names:
            schoon_naam = deep_clean(naam)
            naam_delen = schoon_naam.split()
            
            # We filteren korte woordjes zoals 'van', 'de', 'der' eruit voor de match
            belangrijke_delen = [d for d in naam_delen if len(d) > 2]
            
            if belangrijke_delen:
                for regel in gevalideerde_regels:
                    # Match als ALLE belangrijke delen van de naam in de regel staan
                    if all(deel in regel for deel in belangrijke_delen):
                        st.session_state['matrix'].at[naam, race] = 1
                        gevonden += 1
                        herkende_namen.append(naam)
                        break

        st.success(f"Gereed! {gevonden} renners herkend.")
        st.write("**Nieuw herkend:** " + ", ".join(herkende_namen))

st.divider()
if st.button("Download startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Klik om te downloaden", csv, "startlijsten.csv", "text/csv")
