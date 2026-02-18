import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS Monitor Sync", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    # Accenten verwijderen
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Deense karakters handmatig
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    # Alleen letters en spaties overhouden
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 PCS PDF Updater & Missing Name Monitor")

# 1. Laden van de referentie (WielerOrakel lijst)
try:
    df_ref = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_ref.columns = [c.strip().upper() for c in df_ref.columns]
    master_names = df_ref['NAAM'].tolist()
except Exception as e:
    st.error(f"Kan renners_stats.csv niet laden: {e}")
    st.stop()

# 2. Setup Matrix in Session State
if 'matrix' not in st.session_state:
    try:
        # Probeer bestaande startlijst te laden om op voort te bouwen
        st.session_state['matrix'] = pd.read_csv("startlijsten.csv", index_col='Naam')
    except:
        st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
        st.session_state['matrix'].index.name = "Naam"

race = st.selectbox("Selecteer koers:", st.session_state['matrix'].columns)
plak_veld = st.text_area("Plak hier de PDF tekst (Ctrl+A):", height=300)

if st.button(f"Update {race} & Check op missers"):
    if plak_veld:
        # Reset kolom voor deze koers
        st.session_state['matrix'][race] = 0
        
        regels = plak_veld.split('\n')
        pdf_regels_schoon = []
        originele_regels = []

        # Stap A: Filter op regels die met een nummer beginnen
        for r in regels:
            if re.match(r'^\d+', r.strip()):
                pdf_regels_schoon.append(deep_clean(r))
                originele_regels.append(r.strip())

        herkende_namen = []
        matched_pdf_indices = set()

        # Stap B: Matching van bekende namen
        for naam in master_names:
            schoon_naam = deep_clean(naam)
            naam_delen = [d for d in schoon_naam.split() if len(d) > 2]
            
            if naam_delen:
                for idx, regel_schoon in enumerate(pdf_regels_schoon):
                    # Check of alle delen van de naam in de regel staan
                    if all(deel in regel_schoon for deel in naam_delen):
                        st.session_state['matrix'].at[naam, race] = 1
                        herkende_namen.append(naam)
                        matched_pdf_indices.add(idx)
                        break

        # Stap C: Identificeer missers (Renners in PDF die NIET gematcht zijn)
        missers = [originele_regels[i] for i in range(len(originele_regels)) if i not in matched_pdf_indices]

        # --- OUTPUT ---
        st.success(f"Update voltooid voor {race}!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"✅ Herkend ({len(herkende_namen)})")
            st.write(", ".join(herkende_namen) if herkende_namen else "Geen renners herkend.")
        
        with col2:
            st.subheader(f"⚠️ Niet in je database ({len(missers)})")
            st.caption("Deze renners staan in de PDF maar niet in renners_stats.csv")
            for m in missers:
                st.text(m)

st.divider()
if st.button("💾 Download nieuwe startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Klik om te downloaden", csv, "startlijsten.csv", "text/csv")
