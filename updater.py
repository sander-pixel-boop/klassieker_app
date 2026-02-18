import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS PDF Master Sync - Final", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    # Behoud alleen letters en spaties
    text = re.sub(r'[^a-z\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 PCS PDF Master Updater - Final Precision")

try:
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except:
    st.error("Kan renners_stats.csv niet vinden.")
    st.stop()

# --- OPTIE: BESTAANDE DATA LADEN ---
if 'matrix' not in st.session_state:
    try:
        # We proberen de huidige startlijsten te laden zodat je niet alles verliest
        st.session_state['matrix'] = pd.read_csv("startlijsten.csv", index_col='Naam')
    except:
        st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
        st.session_state['matrix'].index.name = "Naam"

race = st.selectbox("Selecteer koers:", st.session_state['matrix'].columns)
plak_veld = st.text_area("Plak hier de PDF tekst:", height=300)

if st.button(f"Update {race}"):
    if plak_veld:
        st.session_state['matrix'][race] = 0
        regels = plak_veld.split('\n')
        
        # Filter op regels met rugnummers of '---'
        gevalideerde_regels = [deep_clean(r) for r in regels if re.search(r'\d+', r) or "---" in r]

        gevonden = 0
        herkende_namen = []
        
        for naam in master_names:
            schoon_naam = deep_clean(naam)
            naam_delen = [d for d in schoon_naam.split() if len(d) > 2] # Alleen betekenisvolle delen
            
            if niet_leeg := belangrijke_delen = naam_delen:
                for regel in gevalideerde_regels:
                    # MATCH LOGICA:
                    # Als de naam uit 2 delen bestaat (Mads Pedersen), moeten ze allebei in de regel staan.
                    # Als de naam uit 3+ delen bestaat (Henri-François Renard-Haquin), moeten er minstens 2 matchen.
                    match_count = sum(1 for deel in belangrijke_delen if deel in regel)
                    
                    is_match = False
                    if len(belangrijke_delen) <= 2 and match_count == len(belangrijke_delen):
                        is_match = True
                    elif len(belangrijke_delen) > 2 and match_count >= 2:
                        is_match = True
                        
                    if is_match:
                        st.session_state['matrix'].at[naam, race] = 1
                        gevonden += 1
                        herkende_namen.append(naam)
                        break

        st.success(f"Gereed! {gevonden} renners herkend.")
        st.write("**Alle vinkjes voor " + race + ":** " + ", ".join(herkende_namen))

st.divider()
if st.button("Download startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Klik om te downloaden", csv, "startlijsten.csv", "text/csv")
