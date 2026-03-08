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
st.set_page_config(page_title="Giro Team Bouwer", layout="wide", page_icon="🚴")

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
DB_KOLOM = "sporza_giro_team26_v2" # Nieuwe kolom voor versie 2 data

# --- ETAPPE DATA ---
GIRO_ETAPPES = [
    {"id": 1, "date": "08/05", "route": "Nessebar - Burgas", "type": "Vlak", "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 2, "date": "09/05", "route": "Burgas - Valiko Tarnovo", "type": "Heuvel", "w": {"SPR": 0.3, "GC": 0.3, "ITT": 0.0, "MTN": 0.4}},
    {"id": 3, "date": "10/05", "route": "Plovdiv - Sofia", "type": "Vlak", "w": {"SPR": 0.9, "GC": 0.0, "ITT": 0.0, "MTN": 0.1}},
    {"id": 4, "date": "12/05", "route": "Catanzaro - Cosenza", "type": "Vlak/Heuvel", "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 5, "date": "13/05", "route": "Praia a Mare - Potenza", "type": "Heuvel", "w": {"SPR": 0.1, "GC": 0.6, "ITT": 0.0, "MTN": 0.3}},
    {"id": 6, "date": "14/05", "route": "Paestum - Naples", "type": "Vlak/Heuvel", "w": {"SPR": 0.8, "GC": 0.0, "ITT": 0.0, "MTN": 0.2}},
    {"id": 7, "date": "15/05", "route": "Formia - Blockhaus", "type": "Berg", "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 8, "date": "16/05", "route": "Chieti - Fermo", "type": "Heuvel", "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 9, "date": "17/05", "route": "Cervia - Corno alle Scale", "type": "Berg", "w": {"SPR": 0.0, "GC": 0.8, "ITT": 0.0, "MTN": 0.2}},
    {"id": 10, "date": "19/05", "route": "Viareggio - Massa", "type": "Tijdrit", "w": {"SPR": 0.0, "GC": 0.0, "ITT": 1.0, "MTN": 0.0}},
    {"id": 11, "date": "20/05", "route": "Porcari - Chiavari", "type": "Heuvel", "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 12, "date": "21/05", "route": "Imperia - Novi Ligure", "type": "Vlak", "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 13, "date": "22/05", "route": "Alessandria - Verbania", "type": "Heuvel", "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 14, "date": "23/05", "route": "Aosta - Pila", "type": "Berg", "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 15, "date": "24/05", "route": "Voghera - Milan", "type": "Vlak", "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 16, "date": "26/05", "route": "Bellinzona - Carì", "type": "Berg", "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 17, "date": "27/05", "route": "Cassano d'Adda - Andalo", "type": "Heuvel", "w": {"SPR": 0.1, "GC": 0.5, "ITT": 0.0, "MTN": 0.4}},
    {"id": 18, "date": "28/05", "route": "Fai della Paganella - Pieve di Soligo", "type": "Heuvel", "w": {"SPR": 0.3, "GC": 0.2, "ITT": 0.0, "MTN": 0.5}},
    {"id": 19, "date": "29/05", "route": "Feltre - Alleghe", "type": "Berg", "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 20, "date": "30/05", "route": "Gemona del Friuli - Piancavallo", "type": "Berg", "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 21, "date": "31/05", "route": "Rome - Rome", "type": "Vlak", "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
]

# --- HULPFUNCTIES ---
def normalize_name_logic(text):
    if not isinstance(text, str): return ""
    text = text.lower().strip()
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def match_naam_slim(naam, dict_met_namen):
    naam_norm = normalize_name_logic(naam)
    lijst_met_namen = list(dict_met_namen.keys())
    if naam_norm in lijst_met_namen: return dict_met_namen[naam_norm]
    bests = process.extractBests(naam_norm, lijst_met_namen, scorer=fuzz.token_set_ratio, limit=1)
    if bests and bests[0][1] >= 80: return dict_met_namen[bests[0][0]]
    return naam

@st.cache_data
def load_all_data():
    prijzen_file = "giro262/sporza_giro26_startlijst.csv"
    stats_file = "renners_stats.csv"
    if not os.path.exists(prijzen_file) or not os.path.exists(stats_file): return pd.DataFrame()
    
    df_p = pd.read_csv(prijzen_file, sep=None, engine='python')
    df_s = pd.read_csv(stats_file, sep=None, engine='python')
    df_p.columns = df_p.columns.str.strip()
    df_s.columns = df_s.columns.str.strip()
    
    # Matching
    norm_stats = {normalize_name_logic(n): n for n in df_s['Naam'].unique()}
    df_p['MatchNaam'] = df_p['Naam'].apply(lambda x: match_naam_slim(x, norm_stats))
    
    df = pd.merge(df_p, df_s, left_on='MatchNaam', right_on='Naam', how='left', suffixes=('', '_drop'))
    df['Prijs'] = pd.to_numeric(df['Prijs'], errors='coerce').fillna(0)
    # Correctie prijzen
    df.loc[df['Prijs'] > 1000, 'Prijs'] = df['Prijs'] / 1000000
    df.loc[df['Prijs'] == 0.8, 'Prijs'] = 0.75
    
    # EV Berekening
    df['EV'] = ((df['GC']/100)**4 * 400 + (df['SPR']/100)**4 * 250 + (df['ITT']/100)**4 * 80 + (df['MTN']/100)**4 * 100).fillna(0).round(0)
    return df[['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV']].sort_values('Prijs', ascending=False)

# --- APP LOGICA ---
df = load_all_data()
if df.empty:
    st.error("Bestanden niet gevonden!")
    st.stop()

# Initialiseer team in session state
if "my_giro_team" not in st.session_state:
    st.session_state.my_giro_team = []

# --- SIDEBAR: STATUS ---
with st.sidebar:
    st.title("🛡️ Team Status")
    st.markdown(f"*Ingelogd als: {speler_naam}*")
    st.divider()
    
    current_team = df[df['Naam'].isin(st.session_state.my_giro_team)]
    total_spent = current_team['Prijs'].sum()
    num_riders = len(current_team)
    
    # Budget weergave
    colb1, colb2 = st.columns(2)
    colb1.metric("Budget", f"{100-total_spent:.1f}M", delta_color="inverse")
    colb2.metric("Renners", f"{num_riders}/16")
    
    if total_spent > 100: st.error("⚠️ Budget overschreden!")
    if num_riders > 16: st.error("⚠️ Te veel renners!")
    
    # Team checks
    max_team = current_team['Ploeg'].value_counts().max() if not current_team.empty else 0
    if max_team > 3: st.warning(f"⚠️ Let op: {max_team} renners van één ploeg!")

    st.divider()
    if st.button("💾 Team Opslaan", type="primary", use_container_width=True):
        data = {"team": st.session_state.my_giro_team, "ts": datetime.now().isoformat()}
        supabase.table(TABEL_NAAM).update({DB_KOLOM: data}).eq("username", speler_naam).execute()
        st.success("Opgeslagen!")

    if st.button("🔄 Laatst opgeslagen laden", use_container_width=True):
        res = supabase.table(TABEL_NAAM).select(DB_KOLOM).eq("username", speler_naam).execute()
        if res.data and res.data[0].get(DB_KOLOM):
            st.session_state.my_giro_team = res.data[0][DB_KOLOM].get("team", [])
            st.rerun()

    if st.button("🗑️ Team wissen", use_container_width=True):
        st.session_state.my_giro_team = []
        st.rerun()

# --- HOOFDSCHERM ---
st.title("🇮🇹 Handmatige Giro Team Bouwer")
st.markdown("*Data en Statistieken van [Wielerorakel](https://wielerorakel.nl/)*")

t1, t2, t3 = st.tabs(["👥 Renner Selectie", "📈 Team Analyse", "🗺️ Etappe Check"])

with t1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Beschikbare Renners")
        search = st.text_input("Zoek renner of ploeg...", "")
        
        # Filter dataframe
        filtered_df = df.copy()
        if search:
            filtered_df = filtered_df[filtered_df['Naam'].str.contains(search, case=False) | filtered_df['Ploeg'].str.contains(search, case=False)]
        
        # Weergave tabel met knoppen
        for _, row in filtered_df.iterrows():
            is_in_team = row['Naam'] in st.session_state.my_giro_team
            c_name, c_team, c_price, c_btn = st.columns([3, 3, 2, 2])
            c_name.write(f"**{row['Naam']}**")
            c_team.write(f"*{row['Ploeg']}*")
            c_price.write(f"€ {row['Prijs']}M")
            
            if is_in_team:
                if c_btn.button("Verwijder", key=f"rem_{row['Naam']}", type="secondary"):
                    st.session_state.my_giro_team.remove(row['Naam'])
                    st.rerun()
            else:
                if c_btn.button("Voeg toe", key=f"add_{row['Naam']}", type="primary", disabled=(num_riders >= 16)):
                    st.session_state.my_giro_team.append(row['Naam'])
                    st.rerun()
            st.divider()

    with col2:
        st.subheader("Jouw Selectie")
        if not st.session_state.my_giro_team:
            st.info("Nog geen renners geselecteerd.")
        else:
            for r_name in st.session_state.my_giro_team:
                r_info = df[df['Naam'] == r_name].iloc[0]
                st.write(f"✅ {r_name} ({r_info['Prijs']}M)")

with t2:
    if current_team.empty:
        st.info("Voeg eerst renners toe voor analyse.")
    else:
        st.subheader("Kwaliteiten van je team")
        # Gemiddelde scores
        avg_stats = current_team[['GC', 'SPR', 'ITT', 'MTN']].mean()
        st.bar_chart(avg_stats)
        
        st.subheader("Details per renner")
        st.dataframe(current_team[['Naam', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV']], hide_index=True)

with t3:
    st.subheader("Etappe-voorspelling (AI advies op jouw team)")
    if current_team.empty:
        st.warning("Selecteer een team om de etappe-checks te zien.")
    else:
        for etappe in GIRO_ETAPPES:
            w = etappe['w']
            # Bereken score voor deze etappe voor alle renners in jouw team
            current_team_scores = current_team.copy()
            current_team_scores['StageScore'] = (
                current_team_scores['SPR'] * w['SPR'] +
                current_team_scores['GC'] * w['GC'] +
                current_team_scores['ITT'] * w['ITT'] +
                current_team_scores['MTN'] * w['MTN']
            )
            
            best_3 = current_team_scores.sort_values('StageScore', ascending=False).head(3)
            
            with st.expander(f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']})"):
                st.write("**Jouw beste troeven voor vandaag:**")
                for _, b in best_3.iterrows():
                    st.write(f"- {b['Naam']} (Score: {int(b['StageScore'])})")
