import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Bronbeheer Startlijsten", layout="wide")

st.title("📝 Bronbeheer: Nieuws & Geruchten")
st.info("Gebruik dit paneel om handmatig vinkjes te zetten op basis van het laatste nieuws.")

# 1. Laden van de data
@st.cache_data
def load_source():
    if os.path.exists("bron_startlijsten.csv"):
        df = pd.read_csv("bron_startlijsten.csv")
        name_col = 'Naam' if 'Naam' in df.columns else 'NAAM'
        return df.set_index(name_col)
    else:
        # Fallback als bron nog niet bestaat
        df_stats = pd.read_csv("renners_stats.csv")
        name_col = 'Naam' if 'Naam' in df_stats.columns else 'NAAM'
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        df = pd.DataFrame(0, index=df_stats[name_col], columns=races)
        return df

if 'matrix' not in st.session_state:
    st.session_state['matrix'] = load_source()

# 2. Handmatige aanpassingen
with st.expander("Snel zoeken & vinken"):
    search_name = st.text_input("Zoek renner:")
    if search_name:
        matches = st.session_state['matrix'].index[st.session_state['matrix'].index.str.contains(search_name, case=False)]
        selected_renner = st.selectbox("Selecteer:", matches)
        if selected_renner:
            race_to_update = st.selectbox("Voor koers:", st.session_state['matrix'].columns)
            current_val = st.session_state['matrix'].at[selected_renner, race_to_update]
            new_val = st.radio("Status:", [0, 1], index=int(current_val), horizontal=True)
            if st.button("Bijwerken"):
                st.session_state['matrix'].at[selected_renner, race_to_update] = new_val
                st.success(f"{selected_renner} bijgewerkt voor {race_to_update}")

# 3. Overzicht en Export
st.subheader("Huidige Matrix")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Export naar GitHub"):
    # We slaan het op als startlijsten.csv (die de hoofd-app gebruikt)
    csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download startlijsten.csv", csv, "startlijsten.csv", "text/csv")
