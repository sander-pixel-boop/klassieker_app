import streamlit as st
import pandas as pd

st.set_page_config(page_title="Handmatige PCS Sync")

st.title("📋 PCS Data Plak-Tool")
st.write("Omdat PCS de server blokkeert, doen we het zo: kopieer de startlijst op de PCS website en plak de tekst hieronder.")

# Laad de namen die we MOETEN matchen
try:
    base_df = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
    master_names = base_df.iloc[:, 0].tolist()
except:
    st.error("Upload eerst renners_prijzen.csv naar GitHub")
    st.stop()

race = st.selectbox("Voor welke koers plak je data?", ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
plak_veld = st.text_area("Plak hier de volledige tekst van de PCS startlijst pagina (Ctrl+A / Ctrl+V)")

if st.button("Verwerk deze koers"):
    if plak_veld:
        # We kijken simpelweg of de namen uit onze lijst voorkomen in de geplakte tekst
        gevonden = 0
        if 'matrix' not in st.session_state:
            # Maak een lege tabel met 0 voor alle koersen
            st.session_state['matrix'] = pd.DataFrame(0, index=master_names, columns=["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"])
            st.session_state['matrix'].index.name = "Naam"

        for name in master_names:
            if name.lower() in plak_veld.lower():
                st.session_state['matrix'].at[name, race] = 1
                gevonden += 1
        
        st.success(f"Klaar! {gevonden} renners herkend voor {race}.")
        st.dataframe(st.session_state['matrix'])

if 'matrix' in st.session_state:
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("📩 Download startlijsten.csv", csv, "startlijsten.csv", "text/csv")
