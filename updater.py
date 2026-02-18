import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="PCS & News Master Sync", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    # Verwijder alles behalve letters
    text = re.sub(r'[^a-z\s]', ' ', text)
    return " ".join(text.split())

st.title("🔄 Wieler-Updater: Deense & Tussenvoegsel Fix")

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
            
            # Filter tussenvoegsels eruit (van, den, der, etc.)
            # We houden alleen de 'echte' namen over (meestal voornaam + achternaam)
            stopwoorden = {'van', 'den', 'der', 'de', 'het', 'ten', 'ter'}
            belangrijke_delen = [d for d in delen if d not in stopwoorden and len(d) > 2]
            
            if belangrijke_delen:
                # Check of de belangrijkste delen in de tekst staan
                # Voor 'Marijn van den Berg' checkt hij nu op 'marijn' EN 'berg'
                if all(d in tekst_bak for d in belangrijke_delen):
                    st.session_state['matrix'].at[naam, race] = 1
                    herkende_namen.append(naam)
                # Backup check voor namen met koppeltekens die PDF soms splitst
                elif len(belangrijke_delen) > 2:
                    match_count = sum(1 for d in belangrijke_delen if d in tekst_bak)
                    if match_count >= 2:
                        st.session_state['matrix'].at[naam, race] = 1
                        herkende_namen.append(naam)

        st.success(f"Klaar! {len(herkende_namen)} renners herkend voor {race}.")
        with st.expander("Bekijk herkende renners"):
            st.write(", ".join(sorted(herkende_namen)))

st.subheader("Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Download startlijsten.csv"):
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download", csv, "startlijsten.csv", "text/csv")
