import streamlit as st
import pandas as pd
import json
import unicodedata
import os
import base64
from thefuzz import process, fuzz
from supabase import create_client
from datetime import datetime

# --- CONFIGURATIE ---
st.set_page_config(page_title="Giro Etappe Bouwer", layout="wide", page_icon="🇮🇹")

if "ingelogde_speler" not in st.session_state:
    st.warning("⚠️ Je bent niet ingelogd. Ga terug naar de Home pagina.")
    st.stop()

speler_naam = st.session_state["ingelogde_speler"]

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()
TABEL_NAAM = "gebruikers_data_test"
DB_KOLOM = "sporza_giro_team26_v2"

# --- ETAPPE DATA ---
GIRO_ETAPPES = [
    {"id": 1, "date": "08/05", "route": "Nessebar - Burgas", "type": "Vlak"},
    {"id": 2, "date": "09/05", "route": "Burgas - Valiko Tarnovo", "type": "Heuvel"},
    {"id": 3, "date": "10/05", "route": "Plovdiv - Sofia", "type": "Vlak"},
    {"id": 4, "date": "12/05", "route": "Catanzaro - Cosenza", "type": "Vlak/Heuvel"},
    {"id": 5, "date": "13/05", "route": "Praia a Mare - Potenza", "type": "Heuvel"},
    {"id": 6, "date": "14/05", "route": "Paestum - Naples", "type": "Vlak/Heuvel"},
    {"id": 7, "date": "15/05", "route": "Formia - Blockhaus", "type": "Berg"},
    {"id": 8, "date": "16/05", "route": "Chieti - Fermo", "type": "Heuvel"},
    {"id": 9, "date": "17/05", "route": "Cervia - Corno alle Scale", "type": "Berg"},
    {"id": 10, "date": "19/05", "route": "Viareggio - Massa", "type": "Tijdrit"},
    {"id": 11, "date": "20/05", "route": "Porcari - Chiavari", "type": "Heuvel"},
    {"id": 12, "date": "21/05", "route": "Imperia - Novi Ligure", "type": "Vlak"},
    {"id": 13, "date": "22/05", "route": "Alessandria - Verbania", "type": "Heuvel"},
    {"id": 14, "date": "23/05", "route": "Aosta - Pila", "type": "Berg"},
    {"id": 15, "date": "24/05", "route": "Voghera - Milan", "type": "Vlak"},
    {"id": 16, "date": "26/05", "edge": "Bellinzona - Carì", "type": "Berg"},
    {"id": 17, "date": "27/05", "route": "Cassano d'Adda - Andalo", "type": "Heuvel"},
    {"id": 18, "date": "28/05", "route": "Fai della Paganella - Pieve di Soligo", "type": "Heuvel"},
    {"id": 19, "date": "29/05", "route": "Feltre - Alleghe", "type": "Berg"},
    {"id": 20, "date": "30/05", "route": "Gemona del Friuli - Piancavallo", "type": "Berg"},
    {"id": 21, "date": "31/05", "route": "Rome - Rome", "type": "Vlak"},
]

# --- DATA LADEN ---
@st.cache_data
def load_all_data():
    prijzen_file = "giro262/sporza_giro26_startlijst.csv"
    stats_file = "renners_stats.csv"
    if not os.path.exists(prijzen_file) or not os.path.exists(stats_file): return pd.DataFrame()
    
    df_p = pd.read_csv(prijzen_file, sep=None, engine='python')
    df_s = pd.read_csv(stats_file, sep=None, engine='python')
    df_p.columns = df_p.columns.str.strip()
    df_s.columns = df_s.columns.str.strip()
    
    # Simpele merge op naam
    df = pd.merge(df_p, df_s, on='Naam', how='left')
    df['Prijs'] = pd.to_numeric(df['Prijs'], errors='coerce').fillna(0)
    df.loc[df['Prijs'] > 1000, 'Prijs'] = df['Prijs'] / 1000000
    df.loc[df['Prijs'] == 0.8, 'Prijs'] = 0.75
    return df.sort_values('Naam')

df = load_all_data()

# --- SESSION STATE VOOR ETAPPE KEUZES ---
if "etappe_keuzes" not in st.session_state:
    # We slaan per etappe een lijstje van top 3 renners op
    st.session_state.etappe_keuzes = {str(e["id"]): [None, None, None] for e in GIRO_ETAPPES}

# --- BEREKEN HUIDIG TEAM OP BASIS VAN ETAPPE KEUZES ---
def get_team_from_etappes():
    gekozen = set()
    for etappe_id in st.session_state.etappe_keuzes:
        for renner in st.session_state.etappe_keuzes[etappe_id]:
            if renner:
                gekozen.add(renner)
    return list(gekozen)

huidig_team_namen = get_team_from_etappes()
huidig_team_df = df[df['Naam'].isin(huidig_team_namen)]
totaal_prijs = huidig_team_df['Prijs'].sum()
aantal_renners = len(huidig_team_namen)

# --- SIDEBAR OVERZICHT ---
with st.sidebar:
    st.title("📋 Jouw Team Status")
    st.markdown(f"**Budget over:** € {100 - totaal_prijs:.2f}M")
    st.progress(min(totaal_prijs / 100, 1.0))
    
    st.markdown(f"**Team plekken:** {aantal_renners} / 16")
    if aantal_renners > 16:
        st.error("🚨 Te veel unieke renners!")
    if totaal_prijs > 100:
        st.error("🚨 Budget overschreden!")

    st.divider()
    st.subheader("Geselecteerde Renners:")
    for _, r in huidig_team_df.iterrows():
        st.write(f"- {r['Naam']} (€ {r['Prijs']}M)")

    if st.button("💾 Team & Voorspellingen Opslaan", type="primary", use_container_width=True):
        data = {"team": huidig_team_namen, "etappe_keuzes": st.session_state.etappe_keuzes}
        supabase.table(TABEL_NAAM).update({DB_KOLOM: data}).eq("username", speler_naam).execute()
        st.success("Opgeslagen!")

# --- HOOFDSCHERM ---
st.title("🇮🇹 Bouw je team per etappe")
st.markdown("*Data en Statistieken van [Wielerorakel](https://wielerorakel.nl/)*")
st.info("Kies per etappe de renners waarvan jij denkt dat ze gaan scoren. De app bouwt je team van 16 man automatisch op.")

renners_opties = ["-"] + df['Naam'].tolist()

col_rit, col_detail = st.columns([2, 1])

with col_rit:
    for etappe in GIRO_ETAPPES:
        eid = str(etappe["id"])
        with st.expander(f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']})"):
            c1, c2, c3 = st.columns(3)
            
            for i, col in enumerate([c1, c2, c3]):
                current_val = st.session_state.etappe_keuzes[eid][i]
                default_idx = renners_opties.index(current_val) if current_val in renners_opties else 0
                
                keuze = col.selectbox(
                    f"Top {i+1}", 
                    renners_opties, 
                    index=default_idx, 
                    key=f"select_{eid}_{i}"
                )
                
                # Update state
                st.session_state.etappe_keuzes[eid][i] = keuze if keuze != "-" else None

with col_detail:
    st.subheader("Team Balans Analyse")
    if not huidig_team_df.empty:
        # Toon verdeling types
        stats = huidig_team_df[['GC', 'SPR', 'ITT', 'MTN']].mean()
        st.write("Gemiddelde team-stats:")
        st.bar_chart(stats)
        
        # Laat zien welke ritten nog "onbezet" zijn
        onbezet = 0
        for eid, keuzes in st.session_state.etappe_keuzes.items():
            if not any(keuzes):
                onbezet += 1
        
        if onbezet > 0:
            st.warning(f"Je hebt voor {onbezet} ritten nog geen voorspelling gedaan.")
        else:
            st.success("Je hebt voor alle ritten een troef gekozen!")
    else:
        st.write("Begin met het kiezen van renners in de etappes om je team-analyse te zien.")
