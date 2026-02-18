import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Bronbeheer Startlijsten", layout="wide")

st.title("📝 Bronbeheer: Nieuws & Geruchten")

# 1. Laden van de data
@st.cache_data
def load_source():
    # Check of de bron al bestaat
    if os.path.exists("bron_startlijsten.csv"):
        df = pd.read_csv("bron_startlijsten.csv")
    else:
        # Maak een nieuwe basis op basis van de stats
        df_stats = pd.read_csv("renners_stats.csv")
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        # Pak de eerste kolom als naamkolom
        name_col = df_stats.columns[0]
        df = pd.DataFrame(0, index=df_stats[name_col], columns=races).reset_index()
    
    # Forceer NAAM als kolomnaam voor consistentie
    df.columns = ['NAAM'] + list(df.columns[1:])
    return df.set_index('NAAM')

if 'matrix' not in st.session_state:
    st.session_state['matrix'] = load_source()

# 2. Handmatige aanpassingen
with st.expander("Snel zoeken & vinken"):
    search_name = st.text_input("Zoek renner (bijv. 'Van Aert'):")
    if search_name:
        matches = st.session_state['matrix'].index[st.session_state['matrix'].index.str.contains(search_name, case=False)]
        if not matches.empty:
            selected_renner = st.selectbox("Selecteer:", matches)
            race_to_update = st.selectbox("Voor koers:", st.session_state['matrix'].columns)
            current_val = st.session_state['matrix'].at[selected_renner, race_to_update]
            new_val = st.radio("Status:", [0, 1], index=int(current_val), horizontal=True)
            if st.button("Bijwerken"):
                st.session_state['matrix'].at[selected_renner, race_to_update] = new_val
                st.success(f"{selected_renner} bijgewerkt!")
        else:
            st.warning("Geen renner gevonden.")

# 3. Overzicht en Export
st.subheader("Huidige Matrix")
st.dataframe(st.session_state['matrix'])

col1, col2 = st.columns(2)
with col1:
    if st.button("💾 Download bron_startlijsten.csv (voor jezelf)"):
        csv_bron = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
        st.download_button("Download Bron", csv_bron, "bron_startlijsten.csv", "text/csv")

with col2:
    if st.button("🚀 Download startlijsten.csv (voor de App)"):
        csv_app = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
        st.download_button("Download voor App", csv_app, "startlijsten.csv", "text/csv")
