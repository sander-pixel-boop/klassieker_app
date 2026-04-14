import streamlit as st
import pandas as pd
import unicodedata
import os
import base64
import pulp
from app_utils.db import init_connection
from app_utils.giro_data import load_giro_data, calculate_giro_ev

# --- CONFIGURATIE ---
st.set_page_config(page_title="Giro Etappe Bouwer", layout="wide", page_icon="🇮🇹")

if "ingelogde_speler" not in st.session_state:
    st.warning("⚠️ Je bent niet ingelogd. Ga terug naar de Home pagina.")
    st.stop()

speler_naam = st.session_state["ingelogde_speler"]

supabase = init_connection()
TABEL_NAAM = st.secrets.get("TABEL_NAAM", "gebruikers_data_test")
DB_KOLOM = "sporza_giro_team26_v2"

# --- ETAPPE DATA ---
GIRO_ETAPPES = [
    {"id": 1,  "date": "08/05", "route": "Nessebar - Burgas",                       "type": "Vlak",       "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 2,  "date": "09/05", "route": "Burgas - Valiko Tarnovo",                 "type": "Heuvel",     "w": {"SPR": 0.3, "GC": 0.3, "ITT": 0.0, "MTN": 0.4}},
    {"id": 3,  "date": "10/05", "route": "Plovdiv - Sofia",                         "type": "Vlak/Heuvel","w": {"SPR": 0.9, "GC": 0.0, "ITT": 0.0, "MTN": 0.1}},
    {"id": 4,  "date": "12/05", "route": "Catanzaro - Cosenza",                     "type": "Vlak/Heuvel","w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 5,  "date": "13/05", "route": "Praia a Mare - Potenza",                  "type": "Heuvel",     "w": {"SPR": 0.1, "GC": 0.6, "ITT": 0.0, "MTN": 0.3}},
    {"id": 6,  "date": "14/05", "route": "Paestum - Naples",                        "type": "Heuvel",     "w": {"SPR": 0.8, "GC": 0.0, "ITT": 0.0, "MTN": 0.2}},
    {"id": 7,  "date": "15/05", "route": "Formia - Blockhaus",                      "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 8,  "date": "16/05", "route": "Chieti - Fermo",                          "type": "Heuvel",     "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 9,  "date": "17/05", "route": "Cervia - Corno alle Scale",               "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.8, "ITT": 0.0, "MTN": 0.2}},
    {"id": 10, "date": "19/05", "route": "Viareggio - Massa",                       "type": "Tijdrit",    "w": {"SPR": 0.0, "GC": 0.0, "ITT": 1.0, "MTN": 0.0}},
    {"id": 11, "date": "20/05", "route": "Porcari - Chiavari",                      "type": "Heuvel",     "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 12, "date": "21/05", "route": "Imperia - Novi Ligure",                   "type": "Vlak",       "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 13, "date": "22/05", "route": "Alessandria - Verbania",                  "type": "Heuvel",     "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 14, "date": "23/05", "route": "Aosta - Pila",                            "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 15, "date": "24/05", "route": "Voghera - Milan",                         "type": "Vlak",       "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 16, "date": "26/05", "route": "Bellinzona - Carì",                       "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 17, "date": "27/05", "route": "Cassano d'Adda - Andalo",                 "type": "Heuvel",     "w": {"SPR": 0.1, "GC": 0.5, "ITT": 0.0, "MTN": 0.4}},
    {"id": 18, "date": "28/05", "route": "Fai della Paganella - Pieve di Soligo",   "type": "Heuvel",     "w": {"SPR": 0.3, "GC": 0.2, "ITT": 0.0, "MTN": 0.5}},
    {"id": 19, "date": "29/05", "route": "Feltre - Alleghe",                        "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 20, "date": "30/05", "route": "Gemona del Friuli - Piancavallo",         "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 21, "date": "31/05", "route": "Rome - Rome",                             "type": "Vlak",       "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
]

def laad_profiel_scores():
    bestand = "data/giro262/profile_score.csv"
    if os.path.exists(bestand):
        try:
            df_scores = pd.read_csv(bestand, sep=None, engine='python')
            df_scores.columns = df_scores.columns.str.strip()
            for row in df_scores.itertuples():
                try:
                    s_id = int(row.id)
                    for e in GIRO_ETAPPES:
                        if e['id'] == s_id:
                            if 'SPR' in df_scores.columns: e['w']['SPR'] = float(row.SPR)
                            if 'GC'  in df_scores.columns: e['w']['GC']  = float(row.GC)
                            if 'ITT' in df_scores.columns: e['w']['ITT'] = float(row.ITT)
                            if 'MTN' in df_scores.columns: e['w']['MTN'] = float(row.MTN)
                except:
                    continue
        except Exception:
            pass

laad_profiel_scores()

# --- DATA LADEN ---
df_raw = load_giro_data()
if df_raw.empty:
    st.error("Kon geen data inladen. Controleer data/giro262/startlist.csv of data/renners_stats.csv")
    st.stop()

df = calculate_giro_ev(df_raw)


# --- SESSION STATE INITIALISATIE ---
if "concept5_team" not in st.session_state:
    st.session_state.concept5_team = []

# Update sessie state vanuit database
try:
    res = supabase.table(TABEL_NAAM).select(DB_KOLOM).eq("username", speler_naam).execute()
    if res.data and res.data[0].get(DB_KOLOM):
        opgeslagen_team = res.data[0][DB_KOLOM]
        if isinstance(opgeslagen_team, list):
            st.session_state.concept5_team = opgeslagen_team
except Exception as e:
    st.error(f"Fout bij laden van opgeslagen team: {e}")

# --- HEADER & STATS ---
st.title("Giro Team Bouwer - Simpel & Intuïtief")
st.markdown("Selecteer je 16 renners voor de Giro d'Italia. Klik op de checkbox om een renner toe te voegen of te verwijderen.")

# Bereken huidige stats
huidige_selectie_df = df[df['Naam'].isin(st.session_state.concept5_team)]
aantal_geselecteerd = len(st.session_state.concept5_team)
totaal_prijs = huidige_selectie_df['Prijs'].sum()
budget_over = 100.0 - totaal_prijs

col_stat1, col_stat2, col_stat3 = st.columns(3)
col_stat1.metric("Geselecteerde Renners", f"{aantal_geselecteerd} / 16", delta_color="off" if aantal_geselecteerd <= 16 else "inverse")
col_stat2.metric("Budget Resterend", f"€ {budget_over:.1f}M", delta_color="normal" if budget_over >= 0 else "inverse")
col_stat3.metric("Verwachte Waarde (EV)", f"{huidige_selectie_df['EV'].sum():.1f}")

if aantal_geselecteerd > 16:
    st.error("🚨 Je hebt meer dan 16 renners geselecteerd!")
if budget_over < 0:
    st.error("🚨 Je budget is overschreden!")

if st.button("💾 Sla Team Op", type="primary", use_container_width=True, disabled=aantal_geselecteerd != 16 or budget_over < 0, help="Je moet precies 16 renners selecteren en binnen budget blijven." if (aantal_geselecteerd != 16 or budget_over < 0) else None):
    try:
        supabase.table(TABEL_NAAM).update({DB_KOLOM: st.session_state.concept5_team}).eq("username", speler_naam).execute()
        st.success("✅ Team succesvol opgeslagen!")
    except Exception as e:
        st.error(f"Fout bij opslaan: {e}")

st.divider()

# --- RIDER SELECTION ---
# We voegen een boolean kolom toe voor de selectie
display_df = df[['Naam', 'Ploeg', 'Type', 'Prijs', 'EV', 'GC', 'SPR', 'ITT', 'MTN']].copy()
display_df['Geselecteerd'] = display_df['Naam'].isin(st.session_state.concept5_team)

# Zorg dat de Geselecteerd kolom vooraan staat
cols = ['Geselecteerd'] + [col for col in display_df.columns if col != 'Geselecteerd']
display_df = display_df[cols]

# Sorteer standaard op Geselecteerd (True eerst), daarna op Prijs
display_df = display_df.sort_values(['Geselecteerd', 'Prijs'], ascending=[False, False])

st.subheader("Renners Selecteren")
edited_df = st.data_editor(
    display_df,
    column_config={
        "Geselecteerd": st.column_config.CheckboxColumn(
            "Selecteer",
            help="Vink aan om aan je team toe te voegen",
            default=False,
        ),
        "Prijs": st.column_config.NumberColumn(
            "Prijs (€M)",
            format="€%.1fM"
        ),
        "EV": st.column_config.NumberColumn(
            "Verwachte Ptn",
            format="%.1f"
        )
    },
    disabled=["Naam", "Ploeg", "Type", "Prijs", "EV", "GC", "SPR", "ITT", "MTN"],
    hide_index=True,
    use_container_width=True,
    key="rider_editor"
)

# Update state op basis van bewerkte dataframe
nieuwe_selectie = edited_df[edited_df['Geselecteerd']]['Naam'].tolist()

if set(nieuwe_selectie) != set(st.session_state.concept5_team):
    st.session_state.concept5_team = nieuwe_selectie
    st.rerun()

# --- STAGE MATRIX ---
st.divider()
st.subheader("De Koers (Dagelijkse Opstellingen)")

if not st.session_state.concept5_team:
    st.info("Selecteer renners om hun inzetbaarheid per etappe te zien.")
else:
    matrix_data = {renner: {"Renner": renner} for renner in st.session_state.concept5_team}
    huidig_team_df = df[df['Naam'].isin(st.session_state.concept5_team)].copy()

    for etappe in GIRO_ETAPPES:
        col_name = f"E{etappe['id']}"
        for renner in st.session_state.concept5_team:
            matrix_data[renner][col_name] = "-"

        # Calculate stage scores
        w = etappe['w']
        som_input = sum(w.values()) or 1.0
        norm_w = {k: v / som_input for k, v in w.items()}

        huidig_team_df['StageScore'] = (
            huidig_team_df.get('SPR', 0) * norm_w.get('SPR', 0) +
            huidig_team_df.get('GC',  0) * norm_w.get('GC',  0) +
            huidig_team_df.get('ITT', 0) * norm_w.get('ITT', 0) +
            huidig_team_df.get('MTN', 0) * norm_w.get('MTN', 0)
        )

        # Get top 9
        top_9 = huidig_team_df.sort_values('StageScore', ascending=False).head(9)['Naam'].tolist()
        effectief_km = top_9[0] if top_9 else None

        for renner in top_9:
            matrix_data[renner][col_name] = "©" if renner == effectief_km else "✅"

    st.dataframe(pd.DataFrame(list(matrix_data.values())), hide_index=True, use_container_width=True)
