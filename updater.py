import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="WielerOrakel PCS Sync", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    # Verwijder accenten (é -> e, ø -> o)
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd').replace('-', ' ')
    # Behoud alleen letters en spaties
    text = re.sub(r'[^a-z\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 Master Updater: WielerOrakel + Nieuws + PCS")

# 1. LADEN VAN DE REFERENTIE (WielerOrakel - Alle mogelijke renners)
try:
    df_stats = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_stats.columns = [c.strip().upper() for c in df_stats.columns]
    master_names = df_stats['NAAM'].tolist()
except:
    st.error("❌ Kan renners_stats.csv niet vinden. Dit is je Master-lijst.")
    st.stop()

# 2. LADEN VAN HET BRONBESTAND (Jouw Nieuws/Geruchten)
if 'matrix' not in st.session_state:
    try:
        df_bron = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
        # Zorg dat alle renners uit de stats-lijst in onze matrix zitten
        name_col = 'Naam' if 'Naam' in df_bron.columns else 'NAAM'
        df_bron = df_bron.set_index(name_col)
        
        # We maken een nieuwe matrix op basis van ALLE namen van WielerOrakel
        # En we vullen die aan met de vinkjes die je al had in bron_startlijsten
        new_matrix = pd.DataFrame(0, index=master_names, columns=df_bron.columns)
        for col in df_bron.columns:
            # Match vinkjes op basis van index (Naam)
            new_matrix[col] = df_bron[col].reindex(new_matrix.index, fill_value=0)
            
        st.session_state['matrix'] = new_matrix
        st.success("✅ WielerOrakel lijst geladen en aangevuld met jouw nieuws-data.")
    except Exception as e:
        st.warning(f"Geen bron_startlijsten.csv gevonden of fout bij laden. We starten met een lege lijst op basis van WielerOrakel. ({e})")
        # Fallback: start met lege matrix op basis van stats
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=races)

race = st.selectbox("Update koers:", st.session_state['matrix'].columns.tolist())
plak_veld = st.text_area("Plak hier de PCS PDF tekst (Ctrl+A uit de PDF):", height=250)

if st.button(f"Verwerk PCS data voor {race}"):
    if plak_veld:
        # Stap A: Tekstbak maken van de PDF
        tekst_bak = deep_clean(plak_veld)
        
        herkende_namen_pcs = []
        
        # Stap B: Matching
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            # Filter stopwoorden en korte namen
            stopwoorden = {'van', 'den', 'der', 'de', 'het', 'ten', 'ter'}
            naam_delen = [d for d in schoon_naam.split() if d not in stopwoorden and len(d) > 2]
            
            if naam_delen:
                # MATCH: Alle delen van de naam moeten in de tekst voorkomen
                if all(deel in tekst_bak for deel in naam_delen):
                    st.session_state['matrix'].at[naam, race] = 1
                    herkende_namen_pcs.append(naam)
                # Backup voor namen met 3+ delen (bijv. Henri-Francois Renard-Haquin)
                elif len(naam_delen) > 2:
                    if sum(1 for d in naam_delen if d in tekst_bak) >= 2:
                        st.session_state['matrix'].at[naam, race] = 1
                        herkende_namen_pcs.append(naam)

        # Statistieken
        totaal_vinkjes = (st.session_state['matrix'][race] == 1).sum()
        st.metric(label=f"Totaal aantal renners voor {race}", value=int(totaal_vinkjes))
        st.success(f"PCS Check voltooid: {len(herkende_namen_pcs)} renners uit de PDF herkend.")

# 3. OVERZICHT & DOWNLOAD
st.divider()
st.subheader("Overzicht van alle vinkjes")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download startlijsten.csv", csv, "startlijsten.csv", "text/csv")
