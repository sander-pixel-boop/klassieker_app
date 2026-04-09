import streamlit as st
import pandas as pd
import pulp
import json
import os
import base64
from thefuzz import process, fuzz
from utils.db import init_connection
from utils.name_matching import match_naam_slim, normalize_name_logic
from datetime import datetime
from utils.claude_predictions import genereer_claude_etappe_voorspellingen
from utils.giro_data import load_giro_data, calculate_giro_ev
from utils.giro_solver import solve_giro_team

# --- CONFIGURATIE ---
st.set_page_config(page_title="Sporza Giro Suggesties Solver", layout="wide", page_icon="🤖")

if "ingelogde_speler" not in st.session_state:
    st.warning("⚠️ Je bent niet ingelogd. Ga terug naar de Home pagina om in te loggen.")
    st.stop()

speler_naam = st.session_state["ingelogde_speler"]

supabase = init_connection()
TABEL_NAAM = "gebruikers_data_test"
DB_KOLOM = "sporza_giro_team26"

# --- ETAPPE DATA ---
GIRO_ETAPPES = [
    {"id": 1,  "date": "08/05", "route": "Nessebar - Burgas",                        "km": 156,   "type": "Vlak ➖",        "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 2,  "date": "09/05", "route": "Burgas - Valiko Tarnovo",                  "km": 220,   "type": "Heuvel ↗️",      "w": {"SPR": 0.3, "GC": 0.3, "ITT": 0.0, "MTN": 0.4}},
    {"id": 3,  "date": "10/05", "route": "Plovdiv - Sofia",                          "km": 174,   "type": "Vlak/Heuvel",   "w": {"SPR": 0.9, "GC": 0.0, "ITT": 0.0, "MTN": 0.1}},
    {"id": 4,  "date": "12/05", "route": "Catanzaro - Cosenza",                      "km": 144,   "type": "Vlak/Heuvel",   "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 5,  "date": "13/05", "route": "Praia a Mare - Potenza",                   "km": 204,   "type": "Heuvel ↗️",      "w": {"SPR": 0.1, "GC": 0.6, "ITT": 0.0, "MTN": 0.3}},
    {"id": 6,  "date": "14/05", "route": "Paestum - Naples",                         "km": 161,   "type": "Heuvel ↗️",      "w": {"SPR": 0.8, "GC": 0.0, "ITT": 0.0, "MTN": 0.2}},
    {"id": 7,  "date": "15/05", "route": "Formia - Blockhaus",                       "km": 246,   "type": "Berg ⛰️",        "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 8,  "date": "16/05", "route": "Chieti - Fermo",                           "km": 159,   "type": "Heuvel ↗️",      "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 9,  "date": "17/05", "route": "Cervia - Corno alle Scale",                "km": 184,   "type": "Berg ⛰️",        "w": {"SPR": 0.0, "GC": 0.8, "ITT": 0.0, "MTN": 0.2}},
    {"id": 10, "date": "19/05", "route": "Viareggio - Massa",                        "km": 40.2,  "type": "Tijdrit ⏱️",     "w": {"SPR": 0.0, "GC": 0.0, "ITT": 1.0, "MTN": 0.0}},
    {"id": 11, "date": "20/05", "route": "Porcari - Chiavari",                       "km": 178,   "type": "Heuvel ↗️",      "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 12, "date": "21/05", "route": "Imperia - Novi Ligure",                    "km": 177,   "type": "Vlak ➖",        "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 13, "date": "22/05", "route": "Alessandria - Verbania",                   "km": 186,   "type": "Heuvel ↗️",      "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 14, "date": "23/05", "route": "Aosta - Pila",                             "km": 133,   "type": "Berg ⛰️",        "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 15, "date": "24/05", "route": "Voghera - Milan",                          "km": 136,   "type": "Vlak ➖",        "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 16, "date": "26/05", "route": "Bellinzona - Carì",                        "km": 113,   "type": "Berg ⛰️",        "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 17, "date": "27/05", "route": "Cassano d'Adda - Andalo",                  "km": 200,   "type": "Heuvel ↗️",      "w": {"SPR": 0.1, "GC": 0.5, "ITT": 0.0, "MTN": 0.4}},
    {"id": 18, "date": "28/05", "route": "Fai della Paganella - Pieve di Soligo",    "km": 167,   "type": "Heuvel ↗️",      "w": {"SPR": 0.3, "GC": 0.2, "ITT": 0.0, "MTN": 0.5}},
    {"id": 19, "date": "29/05", "route": "Feltre - Alleghe",                         "km": 151,   "type": "Berg ⛰️",        "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 20, "date": "30/05", "route": "Gemona del Friuli - Piancavallo",          "km": 199,   "type": "Berg ⛰️",        "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 21, "date": "31/05", "route": "Rome - Rome",                              "km": 131,   "type": "Vlak ➖",        "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
]

def laad_profiel_scores():
    bestand = "data/giro262/profile_score.csv"
    if os.path.exists(bestand):
        try:
            df_scores = pd.read_csv(bestand, sep=None, engine='python')
            df_scores.columns = df_scores.columns.str.strip()
            for _, row in df_scores.iterrows():
                try:
                    s_id = int(row['id'])
                    for e in GIRO_ETAPPES:
                        if e['id'] == s_id:
                            if 'SPR' in df_scores.columns: e['w']['SPR'] = float(row['SPR'])
                            if 'GC'  in df_scores.columns: e['w']['GC']  = float(row['GC'])
                            if 'ITT' in df_scores.columns: e['w']['ITT'] = float(row['ITT'])
                            if 'MTN' in df_scores.columns: e['w']['MTN'] = float(row['MTN'])
                except:
                    continue
        except Exception as err:
            st.warning(f"Fout bij inladen profile_score.csv: {err}")

laad_profiel_scores()

# --- HULPFUNCTIES ---
def get_clickable_image_html(image_path, fallback_text, link):
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode()
            ext = "png" if image_path.lower().endswith(".png") else "jpeg"
            img_src = f"data:image/{ext};base64,{encoded_string}"
        except Exception:
            img_src = f"https://placehold.co/600x400/eeeeee/000000?text={fallback_text}"
    else:
        img_src = f"https://placehold.co/600x400/eeeeee/000000?text={fallback_text}"
    return f'<a href="{link}" target="_blank"><img src="{img_src}" width="100%" style="border-radius:8px;"></a>'

# --- DATA LADEN ---
def calculate_prediction_ev(df, predictions, top_x):
    pts_map = [50, 40, 30, 25, 20, 16, 14, 12, 10, 8]
    pred_series = pd.Series(0, index=df.index)
    for stage_id, preds in predictions.items():
        for pos in range(min(top_x, len(preds))):
            renner = preds[pos]
            if renner and renner != "-":
                idx = df[df['Renner'] == renner].index
                if not idx.empty:
                    pred_series.loc[idx[0]] += pts_map[pos]
    return pred_series

# --- HOOFDCODE ---
st.title("🤖 Sporza Giro — Suggesties Solver")
st.markdown(
    "Het systeem analyseert alle 21 etappes op basis van parcoursprofiel en rennerdata, en bouwt automatisch "
    "het optimale team. *Data van [Wielerorakel](https://wielerorakel.nl/)*"
)

df_raw = load_giro_data()
if df_raw.empty: st.stop()

# --- SESSIESTATES ---
if "giro_selected_riders"    not in st.session_state: st.session_state.giro_selected_riders    = []
if "giro_stage_predictions"  not in st.session_state: st.session_state.giro_stage_predictions  = {str(s["id"]): [None]*10 for s in GIRO_ETAPPES}
if "giro_weights"            not in st.session_state: st.session_state.giro_weights            = {str(e["id"]): e["w"].copy() for e in GIRO_ETAPPES}
if "giro_reasoning"          not in st.session_state: st.session_state.giro_reasoning          = {}

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 Profiel: {speler_naam.capitalize()}")

    if speler_naam != "gast":
        c_cloud1, c_cloud2 = st.columns(2)
        with c_cloud1:
            if st.button("💾 Opslaan", type="primary", use_container_width=True):
                data = {
                    "selected_riders": st.session_state.giro_selected_riders,
                    "predictions":     st.session_state.giro_stage_predictions,
                    "weights":         st.session_state.giro_weights,
                    "reasoning":       st.session_state.giro_reasoning,
                    "ts":              datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                supabase.table(TABEL_NAAM).update({DB_KOLOM: data}).eq("username", speler_naam).execute()
                st.success("Opgeslagen!")
        with c_cloud2:
            if st.button("🔄 Inladen", use_container_width=True):
                res = supabase.table(TABEL_NAAM).select(DB_KOLOM).eq("username", speler_naam).execute()
                if res.data and res.data[0].get(DB_KOLOM):
                    db_data = res.data[0][DB_KOLOM]
                    st.session_state.giro_selected_riders   = db_data.get("selected_riders", [])
                    st.session_state.giro_stage_predictions = db_data.get("predictions", {str(s["id"]): [None]*10 for s in GIRO_ETAPPES})
                    st.session_state.giro_weights           = db_data.get("weights",      {str(e["id"]): e["w"].copy() for e in GIRO_ETAPPES})
                    st.session_state.giro_reasoning         = db_data.get("reasoning",    {})
                    st.rerun()
    else:
        st.info("Log in met een account om cloud-opslag te gebruiken.")

    st.divider()

    top_x_voorspellingen = st.number_input("Top X per etappe (Suggesties)", 1, 10, 3)
    max_budget           = st.number_input("Budget (Miljoen)", value=100.0)
    max_renners          = st.number_input("Aantal Renners",   value=16)
    max_per_ploeg        = st.number_input("Max per ploeg",    value=3)

    df = calculate_giro_ev(df_raw)
    df['Prediction_EV'] = calculate_prediction_ev(df, st.session_state.giro_stage_predictions, top_x_voorspellingen)
    df['Combined_EV']   = (df['Prediction_EV'] * 1000) + df['Giro_EV']

    with st.expander("🔒 Forceren / Uitsluiten"):
        force_base = st.multiselect("🟢 Moet in team:", options=df['Renner'].tolist(), help="Kies renners die verplicht in je selectie moeten zitten.")
        ban_base   = st.multiselect("🔴 Niet in team:", options=[r for r in df['Renner'].tolist() if r not in force_base], help="Kies renners die de AI absoluut moet negeren.")

    st.divider()
    if st.button("🚀 BEREKEN TEAM (Puur Statistische Suggesties)", type="primary", use_container_width=True):
        with st.spinner("Puur statistisch team berekenen... Dit kan even duren."):
            res = solve_giro_team(df, max_bud=max_budget, max_ren=max_renners, max_per_team=max_per_ploeg, force_base=force_base, ban_base=ban_base, ev_column="Giro_EV")
            if res:
                st.session_state.giro_selected_riders = res
                st.rerun()

    if st.button("🚀 BEREKEN TEAM (Suggesties + Voorspellingen)", use_container_width=True):
        with st.spinner("Team inclusief voorspellingen berekenen... Dit kan even duren."):
            res = solve_giro_team(df, max_bud=max_budget, max_ren=max_renners, max_per_team=max_per_ploeg, force_base=force_base, ban_base=ban_base, ev_column="Combined_EV")
            if res:
                st.session_state.giro_selected_riders = res
                st.rerun()

    st.divider()
    st.markdown("#### 📥 Exporteer")
    export_data = {
        "team":        st.session_state.giro_selected_riders,
        "predictions": st.session_state.giro_stage_predictions,
        "weights":     st.session_state.giro_weights,
    }
    st.download_button(
        label="📄 JSON",
        data=json.dumps(export_data, indent=2),
        file_name="sporza_giro_ai_export.json",
        mime="application/json",
        use_container_width=True,
    )

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Jouw Selectie", "📅 Etappe Voorspellingen Suggesties", "📋 Database", "ℹ️ Uitleg"])

# ── TAB 1: SELECTIE ──────────────────────────────────────────────────────────
with tab1:
    if st.session_state.giro_selected_riders:
        start_team_df = df[df['Renner'].isin(st.session_state.giro_selected_riders)].copy()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Budget over",  f"€ {max_budget - start_team_df['Prijs'].sum():.2f}M")
        m2.metric("🚴 Renners",      f"{len(start_team_df)} / {max_renners}")
        m3.metric("🎯 EV (Statistische Suggesties)", f"{start_team_df['Giro_EV'].sum()}")
        m4.metric("🏆 EV (Voorspellingen)", f"{start_team_df['Prediction_EV'].sum()}")
        st.dataframe(
            start_team_df[['Renner', 'Team', 'Prijs', 'Type', 'Giro_EV', 'Waarde (EV/M)']].sort_values(by='Prijs', ascending=False),
            hide_index=True, use_container_width=True
        )
    else:
        st.info("👈 Klik op **Bereken Team** in de zijbalk om een optimale selectie te laten samenstellen.")

# ── TAB 2: VOORSPELLINGEN SUGGESTIES ─────────────────────────────────────────
with tab2:
    st.subheader("🤖 Etappe Voorspellingen Suggesties")
    st.info(
        "Het systeem analyseert het parcoursprofiel en de wegingen van alle 21 etappes en kiest automatisch "
        "de sterkste renners per rit. Pas de wegingen per etappe aan om de suggesties te sturen."
    )

    c1, c2 = st.columns([1, 4])
    if c1.button("🤖 Analyseer alle 21 etappes", type="primary"):
        preds, reasoning = genereer_claude_etappe_voorspellingen(
            df,
            GIRO_ETAPPES,
            top_x_voorspellingen,
            st.session_state.giro_weights,
        )
        st.session_state.giro_stage_predictions = preds
        st.session_state.giro_reasoning         = reasoning
        st.rerun()

    if c2.button("🗑️ Wis suggesties"):
        st.session_state.giro_stage_predictions = {str(s["id"]): [None]*10 for s in GIRO_ETAPPES}
        st.session_state.giro_reasoning         = {}
        st.rerun()

    # Per-etappe weging + suggesties output
    for etappe in GIRO_ETAPPES:
        stage_id = str(etappe["id"])
        cw = st.session_state.giro_weights[stage_id]

        som_header  = sum(cw.values()) if sum(cw.values()) > 0 else 1.0
        weight_str  = (
            f"SPR:{int((cw['SPR']/som_header)*100)}% "
            f"GC:{int((cw['GC']/som_header)*100)}% "
            f"ITT:{int((cw['ITT']/som_header)*100)}% "
            f"MTN:{int((cw['MTN']/som_header)*100)}%"
        )

        # Check of er suggesties picks zijn voor deze etappe
        ai_picks = [p for p in st.session_state.giro_stage_predictions.get(stage_id, []) if p]
        picks_badge = f" ✅ {', '.join(ai_picks[:3])}" if ai_picks else ""

        with st.expander(f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']}) | 🎯 {weight_str}{picks_badge}"):

            giro_link = "https://www.giroditalia.it/en/the-route/"
            map_path  = f"giro262/giro26-{etappe['id']}-map.jpg"
            prof_path = f"giro262/giro26-{etappe['id']}-hp.jpg"

            st.markdown("*(Klik op een afbeelding voor de officiële info)*")
            i1, i2 = st.columns(2)
            i1.markdown(get_clickable_image_html(map_path,  f"Kaart+Etappe+{etappe['id']}", giro_link), unsafe_allow_html=True)
            i2.markdown(get_clickable_image_html(prof_path, f"Profiel+Etappe+{etappe['id']}", giro_link), unsafe_allow_html=True)

            st.divider()

            # Weight sliders
            st.markdown("###### ⚙️ Pas de weging aan:")
            wc1, wc2, wc3, wc4 = st.columns(4)
            new_spr = wc1.number_input("Sprint (SPR)",      0.0, 1.0, float(cw["SPR"]), 0.1, key=f"wspr_{stage_id}")
            new_gc  = wc2.number_input("Klassement (GC)",   0.0, 1.0, float(cw["GC"]),  0.1, key=f"wgc_{stage_id}")
            new_itt = wc3.number_input("Tijdrit (ITT)",     0.0, 1.0, float(cw["ITT"]), 0.1, key=f"witt_{stage_id}")
            new_mtn = wc4.number_input("Klim/Aanval (MTN)", 0.0, 1.0, float(cw["MTN"]), 0.1, key=f"wmtn_{stage_id}")

            st.session_state.giro_weights[stage_id] = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}

            som_input = new_spr + new_gc + new_itt + new_mtn
            if abs(som_input - 1.0) > 0.01 and som_input > 0:
                active_weights = {"SPR": new_spr/som_input, "GC": new_gc/som_input,
                                  "ITT": new_itt/som_input, "MTN": new_mtn/som_input}
                st.warning(f"⚠️ Weging telt op tot {som_input*100:.0f}% — wordt automatisch herschaald naar 100%.")
            elif som_input == 0:
                active_weights = {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
                st.error("⚠️ Weging mag niet 0% zijn.")
            else:
                active_weights = st.session_state.giro_weights[stage_id]

            # Static suggesties top-5
            df_stage = df.copy()
            df_stage['StageScore'] = (
                df_stage['SPR'] * active_weights['SPR'] +
                df_stage['GC']  * active_weights['GC']  +
                df_stage['ITT'] * active_weights['ITT'] +
                df_stage['MTN'] * active_weights['MTN']
            )
            top_5       = df_stage.sort_values(by=['StageScore', 'Giro_EV'], ascending=[False, False]).head(5)
            top_5_namen = [f"{r} ({int(s)})" for r, s in top_5[['Renner', 'StageScore']].values]
            st.info(f"💡 **Stat Top 5:** {', '.join(top_5_namen)}")

            # Claude reasoning + picks
            stage_reasoning = st.session_state.giro_reasoning.get(stage_id, "")
            if stage_reasoning:
                st.markdown(
                    f"<div style='border-left:3px solid #1D9E75;padding:10px 14px;"
                    f"border-radius:0 4px 4px 0;margin:8px 0 12px 0;font-size:14px;'>"
                    f"🧠 <strong>Claude:</strong> {stage_reasoning}</div>",
                    unsafe_allow_html=True,
                )

            if ai_picks:
                st.success(f"**Suggesties:** {', '.join(ai_picks)}")
            else:
                st.caption("Nog geen suggesties — klik op **Analyseer alle 21 etappes** hierboven.")

# ── TAB 3: DATABASE ────────────────────────────────────────────────────────────
with tab3:
    st.dataframe(df.sort_values('Giro_EV', ascending=False), hide_index=True, use_container_width=True)

# ── TAB 4: UITLEG ──────────────────────────────────────────────────────────────
with tab4:
    st.header("ℹ️ Uitleg: Suggesties Solver")

    st.warning("""
    **⚠️ LET OP: Voorlopige Data!**
    De startlijst en Sporza-prijzen zijn nog niet definitief. Ze worden bijgewerkt zodra de officiële Giro-lancering plaatsvindt.
    """)

    st.markdown("""
    ### 🤖 Wat doet de Suggesties Solver?

    Deze pagina is volledig **systeem-gestuurd** — jij stelt de parameters in, het systeem doet de rest.

    **Stap 1 — Wegingen aanpassen (optioneel)**
    Elke etappe heeft een standaardweging op basis van het profiel. In Tab 2 kun je per etappe de balans
    tussen Sprint, Klassement, Tijdrit en Klimmen/Aanval verschuiven. Het systeem gebruikt deze wegingen om
    renners te selecteren die het best passen bij elke rit.

    **Stap 2 — Claude analyseert (Tab 2)**
    Klik op *Analyseer alle 21 etappes*. Claude ontvangt de volledige startlijst, alle statssores en
    de parcourswegingen in één prompt, en kiest per etappe de top-X renners. Per etappe verschijnt
    ook een korte 🧠 toelichting waarom die renners de beste keuze zijn.

    **Stap 3 — Team berekenen (zijbalk)**
    - *Puur Statistische Suggesties*: de solver optimaliseert puur op de wiskundige EV-scores (macht-4 curve).
    - *Suggesties + Voorspellingen*: de solver weegt de geselecteerde picks mee als extra bonus, zodat renners
      die Claude vaker noemt meer kans hebben geselecteerd te worden.

    ### ⚙️ Wegingen uitleg
    | Weging | Betekenis |
    |---|---|
    | **SPR** | Sprinters en klassieke renners profiteren van vlakke aankomsten |
    | **GC** | Zware bergritten zijn domein van de topklimmers |
    | **ITT** | Tijdritspecialisten hebben een voordeel op de TT-etappes |
    | **MTN** | Aanvallers, punchers en vluchters kunnen hier scoren |

    > *Vereist: `ANTHROPIC_API_KEY` in `.streamlit/secrets.toml`*
    """)
