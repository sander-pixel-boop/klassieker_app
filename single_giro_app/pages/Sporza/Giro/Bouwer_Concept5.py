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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Titillium Web', sans-serif;
}

/* Main background */
[data-testid="stAppViewContainer"] {
    background-color: #0b0514;
    background-image: radial-gradient(circle at 50% 0%, #2b1154 0%, #0b0514 60%);
    color: white;
}

[data-testid="stHeader"] {
    background-color: transparent;
}

h1, h2, h3 {
    color: white !important;
    font-family: 'Titillium Web', sans-serif !important;
    text-transform: uppercase;
}

h1 { font-weight: 900 !important; }
h2, h3 { font-weight: 700 !important; }

/* Let paragraphs stay normal */
p {
    font-family: 'Titillium Web', sans-serif !important;
    color: #dcdcdc;
}

/* Primary buttons */
button[kind="primary"] {
    background-color: #f672ff !important;
    color: white !important;
    font-weight: 900 !important;
    border: none !important;
    text-transform: uppercase;
    border-radius: 4px !important;
}
button[kind="primary"]:hover {
    background-color: #e55ce0 !important;
}

/* Secondary buttons */
button[kind="secondary"] {
    background-color: rgba(43, 17, 84, 0.7) !important;
    color: white !important;
    border: 1px solid #4a2c7a !important;
    font-weight: 700 !important;
}
button[kind="secondary"]:hover {
    border-color: #f672ff !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background-color: #1a0b2e !important;
    border: 1px solid #4a2c7a !important;
    border-radius: 8px !important;
}

[data-testid="stExpander"] > details > summary {
    background-color: #240f40 !important;
}

[data-testid="stExpander"] > details > summary p {
    color: white !important;
    font-weight: 700 !important;
    text-transform: uppercase;
}

/* Metric boxes */
[data-testid="stMetricValue"] {
    font-weight: 900 !important;
    color: #f672ff !important;
}

[data-testid="stMetricLabel"] {
    color: white !important;
    text-transform: uppercase;
}

</style>
""", unsafe_allow_html=True)

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
if "c5_stage_starters" not in st.session_state:
    st.session_state.c5_stage_starters = {}
if "c5_stage_captains" not in st.session_state:
    st.session_state.c5_stage_captains = {}
if "c5_stage_winners" not in st.session_state:
    st.session_state.c5_stage_winners = {}

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

# --- ETAPPES & MOGELIJKE WINNAARS ---
st.divider()
st.subheader("Stap 1: Mogelijke Winnaars per Etappe")
st.markdown("Kies per etappe tot 3 mogelijke winnaars of renners die veel punten gaan scoren. Deze keuzes helpen je om straks je team samen te stellen.")

def get_stage_suggestions_all(etappe, df_all, n=5):
    w = etappe['w']
    som_input = sum(w.values()) or 1.0
    norm_w = {k: v / som_input for k, v in w.items()}

    df_avail = df_all.copy()
    if df_avail.empty:
        return []

    df_avail['TempStageScore'] = (
        df_avail.get('SPR', 0) * norm_w.get('SPR', 0) +
        df_avail.get('GC',  0) * norm_w.get('GC',  0) +
        df_avail.get('ITT', 0) * norm_w.get('ITT', 0) +
        df_avail.get('MTN', 0) * norm_w.get('MTN', 0)
    )

    suggestions = df_avail.sort_values('TempStageScore', ascending=False).head(n)
    return suggestions.to_dict('records')

for etappe in GIRO_ETAPPES:
    eid = str(etappe['id'])
    with st.expander(f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']})"):
        # Suggesties sectie
        suggesties = get_stage_suggestions_all(etappe, df, n=5)
        if suggesties:
            st.markdown("💡 **Top 5 Suggesties voor deze etappe:**")
            sug_cols = st.columns(len(suggesties))
            for i, sug in enumerate(suggesties):
                with sug_cols[i]:
                    prijs = sug['Prijs']
                    naam = sug['Naam']
                    score = sug['TempStageScore']

                    is_selected = naam in st.session_state.c5_stage_winners.get(eid, [])
                    vol = len(st.session_state.c5_stage_winners.get(eid, [])) >= 3

                    if is_selected:
                        if st.button(f"✅ {naam}\n€{prijs:.1f}M", key=f"sug_win_{eid}_{i}_{naam}", help=f"Verwachte etappe score: {score:.1f}", use_container_width=True):
                            st.session_state.c5_stage_winners[eid].remove(naam)
                            st.rerun()
                    else:
                        disabled = vol
                        help_text = f"Verwachte etappe score: {score:.1f}" if not vol else "Je hebt al 3 winnaars gekozen voor deze etappe."
                        if st.button(f"➕ {naam}\n€{prijs:.1f}M", key=f"sug_win_{eid}_{i}_{naam}", disabled=disabled, help=help_text, use_container_width=True):
                            huidige = st.session_state.c5_stage_winners.get(eid, [])
                            st.session_state.c5_stage_winners[eid] = huidige + [naam]
                            st.rerun()
            st.markdown("---")

        col1, col2 = st.columns([1, 1])
        with col1:
            img_path = f"data/giro262/giro26-{etappe['id']}-hp.jpg"
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.info("Geen profiel beschikbaar.")
        with col2:
            selected_winners = st.multiselect(
                "Kies tot 3 mogelijke winnaars",
                options=df['Naam'].tolist(),
                default=st.session_state.c5_stage_winners.get(eid, []),
                max_selections=3,
                key=f"winners_select_{eid}"
            )
            st.session_state.c5_stage_winners[eid] = selected_winners


# --- RIDER SELECTION ---
st.divider()
st.subheader("Stap 2: Team Selecteren")
st.markdown("Selecteer hieronder je 16 renners voor de Giro d'Italia. Je kunt zien hoe vaak je een renner in de vorige stap als mogelijke winnaar hebt aangeduid.")

# Bereken Etappe Picks
etappe_picks_count = {naam: 0 for naam in df['Naam']}
for winners in st.session_state.c5_stage_winners.values():
    for w in winners:
        if w in etappe_picks_count:
            etappe_picks_count[w] += 1

# We voegen een boolean kolom toe voor de selectie
display_df = df[['Naam', 'Ploeg', 'Type', 'Prijs', 'EV', 'GC', 'SPR', 'ITT', 'MTN']].copy()
display_df['Geselecteerd'] = display_df['Naam'].isin(st.session_state.concept5_team)
display_df['Etappe Picks'] = display_df['Naam'].map(etappe_picks_count)

# Zorg dat de Geselecteerd kolom vooraan staat
cols = ['Geselecteerd'] + [col for col in display_df.columns if col != 'Geselecteerd']
display_df = display_df[cols]

# Sorteer standaard op Geselecteerd (True eerst), dan Etappe Picks (desc), daarna op Prijs
display_df = display_df.sort_values(['Geselecteerd', 'Etappe Picks', 'Prijs'], ascending=[False, False, False])

edited_df = st.data_editor(
    display_df,
    column_config={
        "Geselecteerd": st.column_config.CheckboxColumn(
            "Selecteer",
            help="Vink aan om aan je team toe te voegen",
            default=False,
        ),
        "Etappe Picks": st.column_config.NumberColumn(
            "Winnaar Picks",
            help="Hoe vaak geselecteerd als mogelijke winnaar in de etappes",
            format="%d"
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
    disabled=["Naam", "Ploeg", "Type", "Prijs", "EV", "GC", "SPR", "ITT", "MTN", "Etappe Picks"],
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
if st.session_state.concept5_team:
    st.divider()
    st.subheader("Stap 3: Opstellingen (9 Starters & Kopman)")
    st.markdown("Kies per etappe je 9 starters en kopman uit je geselecteerde team van 16.")

    huidig_team_df = df[df['Naam'].isin(st.session_state.concept5_team)].copy()

    def auto_fill_stage(etappe, team_df):
        if team_df.empty:
            return [], None
        w = etappe['w']
        som_input = sum(w.values()) or 1.0
        norm_w = {k: v / som_input for k, v in w.items()}

        team_df['StageScore'] = (
            team_df.get('SPR', 0) * norm_w.get('SPR', 0) +
            team_df.get('GC',  0) * norm_w.get('GC',  0) +
            team_df.get('ITT', 0) * norm_w.get('ITT', 0) +
            team_df.get('MTN', 0) * norm_w.get('MTN', 0)
        )

        top_9 = team_df.sort_values('StageScore', ascending=False).head(9)['Naam'].tolist()
        capt = top_9[0] if top_9 else None
        return top_9, capt

    if st.button("🤖 Vul alle opstellingen automatisch in", type="primary", use_container_width=True):
        for etappe in GIRO_ETAPPES:
            eid = str(etappe['id'])
            starters, capt = auto_fill_stage(etappe, huidig_team_df.copy())
            st.session_state.c5_stage_starters[eid] = starters
            st.session_state.c5_stage_captains[eid] = capt
            # Explicitly update the widget keys to ensure the UI updates
            st.session_state[f"starters_{eid}"] = starters
            st.session_state[f"capt_{eid}"] = capt
        st.rerun()

    for etappe in GIRO_ETAPPES:
        eid = str(etappe['id'])
        with st.expander(f"Opstelling Etappe {etappe['id']}: {etappe['route']} ({etappe['type']})"):
            col1, col2 = st.columns([1, 1])
            with col1:
                img_path = f"data/giro262/giro26-{etappe['id']}-hp.jpg"
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    st.info("Geen profiel beschikbaar.")
            with col2:
                # Clean up state if team members changed
                valid_team = st.session_state.concept5_team

                if eid in st.session_state.c5_stage_starters:
                    st.session_state.c5_stage_starters[eid] = [r for r in st.session_state.c5_stage_starters[eid] if r in valid_team]
                    if st.session_state.c5_stage_captains.get(eid) not in valid_team:
                        st.session_state.c5_stage_captains[eid] = st.session_state.c5_stage_starters[eid][0] if st.session_state.c5_stage_starters[eid] else None

                # Set defaults if not in state
                if eid not in st.session_state.c5_stage_starters:
                    starters, capt = auto_fill_stage(etappe, huidig_team_df.copy())
                    st.session_state.c5_stage_starters[eid] = starters
                    st.session_state.c5_stage_captains[eid] = capt

                selected_starters = st.multiselect(
                    "Kies 9 starters",
                    options=st.session_state.concept5_team,
                    default=st.session_state.c5_stage_starters[eid],
                    max_selections=9,
                    key=f"starters_{eid}"
                )
                st.session_state.c5_stage_starters[eid] = selected_starters

                # Ensure captain is valid
                capt_options = selected_starters if selected_starters else st.session_state.concept5_team
                current_capt = st.session_state.c5_stage_captains.get(eid)
                capt_idx = capt_options.index(current_capt) if current_capt in capt_options else 0

                if capt_options:
                    selected_capt = st.selectbox(
                        "Kies Kopman (x2 ptn)",
                        options=capt_options,
                        index=capt_idx,
                        key=f"capt_{eid}"
                    )
                    st.session_state.c5_stage_captains[eid] = selected_capt
                else:
                    st.info("Kies eerst starters om een kopman te selecteren.")
                    st.session_state.c5_stage_captains[eid] = None

    st.divider()
    st.subheader("De Koers Matrix")

    matrix_data = {renner: {"Renner": renner} for renner in st.session_state.concept5_team}

    for etappe in GIRO_ETAPPES:
        eid = str(etappe['id'])
        col_name = f"E{etappe['id']}"
        for renner in st.session_state.concept5_team:
            matrix_data[renner][col_name] = "-"

        # Use user selections from session state
        starters = st.session_state.c5_stage_starters.get(eid, [])
        effectief_km = st.session_state.c5_stage_captains.get(eid)

        for renner in starters:
            if renner in matrix_data:
                matrix_data[renner][col_name] = "©" if renner == effectief_km else "✅"

    st.dataframe(pd.DataFrame(list(matrix_data.values())), hide_index=True, use_container_width=True)
