import streamlit as st
import pandas as pd

st.set_page_config(page_title="Klassiekers 2026 - Team Builder", layout="wide")

@st.cache_data
def load_data():
    # Lees het bronbestand in
    df = pd.read_csv("bron_startlijsten.csv")
    
    # Haal de koersnamen dynamisch op (alles na 'Renner' en 'Prijs')
    race_cols = df.columns[2:].tolist()
    
    # Maak een handige weergave-kolom voor de multiselect (bijv. "Pogacar - 7.0M")
    df['Display'] = df['Renner'] + " - " + (df['Prijs'] / 1000000).astype(str) + "M"
    return df, race_cols

df, race_cols = load_data()

st.title("🚴‍♂️ Klassiekers 2026 - Team Builder")

# --- 1. Team Selectie ---
st.header("1. Selecteer je Team (Max 20)")
selected_display = st.multiselect(
    "Zoek en selecteer je renners:", 
    options=df['Display'].tolist(),
    max_selections=20
)

if selected_display:
    # Filter de geselecteerde renners
    selected_df = df[df['Display'].isin(selected_display)].copy()
    
    # --- 2. Budget Berekening ---
