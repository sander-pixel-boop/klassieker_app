import streamlit as st
import pandas as pd
import unicodedata
import os
import base64
import pulp
from utils.db import init_connection
from utils.giro_data import load_giro_data, calculate_giro_ev
from utils.giro_solver import solve_giro_team

# --- CONFIGURATIE ---
st.set_page_config(page_title="Giro Etappe Bouwer", layout="wide", page_icon="🇮🇹")

if "ingelogde_speler" not in st.session_state:
    st.warning("⚠️ Je bent niet ingelogd. Ga terug naar de Home pagina.")
    st.stop()

speler_naam = st.session_state["ingelogde_speler"]

supabase = init_connection()
TABEL_NAAM = "gebruikers_data_test"
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

# --- HULPFUNCTIES ---
def bereken_alle_stage_scores(df_input, wegingen):
    """
    Berekent de stage score voor alle renners in df_input op basis van de wegingen
    en voegt deze toe als een nieuwe kolom 'StageScore'.
    """
    df_out = df_input.copy()
    som_input = sum(wegingen.values()) or 1.0
    w = {k: v / som_input for k, v in wegingen.items()}
    df_out['StageScore'] = (
        df_out.get('SPR', 0) * w.get('SPR', 0) +
        df_out.get('GC',  0) * w.get('GC',  0) +
        df_out.get('ITT', 0) * w.get('ITT', 0) +
        df_out.get('MTN', 0) * w.get('MTN', 0)
    )
    return df_out

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

def bepaal_auto_kopman(team_renners, etappe_id, df):
    """Berekent de automatische kopman puur op basis van het etappeprofiel."""
    w = next((e['w'] for e in GIRO_ETAPPES if e['id'] == etappe_id), {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25})
    df_team = df[df['Naam'].isin(team_renners)]
    if df_team.empty: return None
    df_gescoord = bereken_alle_stage_scores(df_team, w)
    best = df_gescoord.loc[df_gescoord['StageScore'].idxmax()]
    return best['Naam']

# --- DATA LADEN ---
df_raw = load_giro_data()
if df_raw.empty:
    st.error("Databestanden niet gevonden.")
    st.stop()
df = calculate_giro_ev(df_raw)

# --- SESSION STATE ---
_default_keuzes  = {str(e["id"]): [None, None, None] for e in GIRO_ETAPPES}
_default_weights = {str(e["id"]): e["w"].copy()      for e in GIRO_ETAPPES}
_default_kopman  = {str(e["id"]): None               for e in GIRO_ETAPPES}

if "etappe_keuzes"  not in st.session_state: st.session_state.etappe_keuzes  = _default_keuzes.copy()
if "giro_weights_v2" not in st.session_state: st.session_state.giro_weights_v2 = _default_weights.copy()
if "finaal_team"    not in st.session_state: st.session_state.finaal_team    = []
if "kopman_keuzes"  not in st.session_state: st.session_state.kopman_keuzes  = _default_kopman.copy()

huidig_team_namen = st.session_state.finaal_team
huidig_team_df    = df[df['Naam'].isin(huidig_team_namen)].copy() if not df.empty else pd.DataFrame()
totaal_prijs      = huidig_team_df['Prijs'].sum() if not huidig_team_df.empty else 0
aantal_renners    = len(huidig_team_namen)

# --- SIDEBAR ---
with st.sidebar:
    st.title("📋 Team Status")
    st.metric("Budget over", f"€ {100 - totaal_prijs:.2f}M")
    st.metric("Renners",     f"{aantal_renners} / 16")
    if aantal_renners > 16: st.error("🚨 Te veel renners!")
    if totaal_prijs > 100:  st.error("🚨 Budget overschreden!")

    st.divider()

    if speler_naam != "gast":
        if st.button("💾 Opslaan", type="primary", use_container_width=True):
            data = {
                "team":          st.session_state.finaal_team,
                "etappe_keuzes": st.session_state.etappe_keuzes,
                "weights":       st.session_state.giro_weights_v2,
                "kopman_keuzes": st.session_state.kopman_keuzes,
            }
            supabase.table(TABEL_NAAM).update({DB_KOLOM: data}).eq("username", speler_naam).execute()
            st.success("Opgeslagen!")

        if st.button("🔄 Inladen", use_container_width=True):
            res = supabase.table(TABEL_NAAM).select(DB_KOLOM).eq("username", speler_naam).execute()
            if res.data and res.data[0].get(DB_KOLOM):
                db_data = res.data[0][DB_KOLOM]
                st.session_state.etappe_keuzes  = db_data.get("etappe_keuzes",  _default_keuzes.copy())
                st.session_state.giro_weights_v2 = db_data.get("weights",       _default_weights.copy())
                st.session_state.finaal_team    = db_data.get("team",           [])
                st.session_state.kopman_keuzes  = db_data.get("kopman_keuzes",  _default_kopman.copy())
                st.rerun()
    else:
        st.info("Log in met een account om cloud-opslag te gebruiken.")

    # Kopman snelknoppen
    if huidig_team_namen:
        st.divider()
        st.markdown("#### 🎖️ Kopman beheer")
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            if st.button("🔄 Reset\nalle kopmannen", use_container_width=True,
                         help="Zet alle etappes terug naar automatisch"):
                st.session_state.kopman_keuzes = _default_kopman.copy()
                st.rerun()
        with col_k2:
            ingesteld = sum(1 for v in st.session_state.kopman_keuzes.values() if v is not None)
            st.metric("Handmatig", f"{ingesteld}/21")

# --- HOOFDSCHERM ---
st.title("🗂️ Concept 1: Master-Detail Layout")
st.markdown("*Data en Statistieken van [Wielerorakel](https://wielerorakel.nl/)*")

if df.empty:
    st.error("Databestanden niet gevonden.")
    st.stop()

# Master-Detail Layout
col_nav, col_stage, col_team = st.columns([1, 2.5, 1.5])

# Left Column: Navigation
with col_nav:
    st.subheader("📍 Etappes")

    if "aktieve_etappe_idx" not in st.session_state:
        st.session_state.aktieve_etappe_idx = 0

    for i, e in enumerate(GIRO_ETAPPES):
        eid_str = str(e["id"])
        keuzes = [k for k in st.session_state.etappe_keuzes.get(eid_str, []) if k]
        status = "🟢" if len(keuzes) > 0 else "⚪"

        button_style = "primary" if st.session_state.aktieve_etappe_idx == i else "secondary"

        if st.button(f"{status} E{e['id']} - {e['type']}", key=f"nav_{i}", use_container_width=True, type=button_style):
            st.session_state.aktieve_etappe_idx = i
            st.rerun()

    st.markdown("---")
    if st.button("🤖 Auto-vul Alle Etappes", use_container_width=True):
        for e in GIRO_ETAPPES:
            eid_str = str(e["id"])
            cw = st.session_state.giro_weights_v2[eid_str]
            som_input = sum(cw.values())
            w = {k: v / som_input for k, v in cw.items()} if som_input > 0 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
            df_stage = bereken_alle_stage_scores(df, w)
            top_3_pure_names = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False])['Naam'].tolist()[:3]
            for idx, naam in enumerate(top_3_pure_names):
                st.session_state.etappe_keuzes[eid_str][idx] = naam
        st.rerun()

# Middle Column: Active Stage Workspace
with col_stage:
    etappe = GIRO_ETAPPES[st.session_state.aktieve_etappe_idx]
    eid    = str(etappe["id"])
    cw     = st.session_state.giro_weights_v2[eid]

    st.subheader(f"Etappe {etappe['id']}: {etappe['route']}")

    c_meta1, c_meta2 = st.columns(2)
    c_meta1.metric("Type", etappe["type"])
    c_meta2.metric("Datum", etappe["date"])

    with st.expander("⚙️ Etappeprofiel weging & Kaart", expanded=False):
        # Maps
        giro_link = "https://www.giroditalia.it/en/the-route/"
        map_path  = f"data/giro262/giro26-{etappe['id']}-map.jpg"
        prof_path = f"data/giro262/giro26-{etappe['id']}-hp.jpg"
        i1, i2 = st.columns(2)
        i1.markdown(get_clickable_image_html(map_path,  f"Kaart+{etappe['id']}", giro_link), unsafe_allow_html=True)
        i2.markdown(get_clickable_image_html(prof_path, f"Profiel+{etappe['id']}", giro_link), unsafe_allow_html=True)

        st.divider()
        wc1, wc2 = st.columns(2)
        new_spr = wc1.number_input("Sprint (SPR)",      0.0, 1.0, float(cw["SPR"]), 0.1, key=f"wspr_{eid}")
        new_gc  = wc1.number_input("Klassement (GC)",   0.0, 1.0, float(cw["GC"]),  0.1, key=f"wgc_{eid}")
        new_itt = wc2.number_input("Tijdrit (ITT)",     0.0, 1.0, float(cw["ITT"]), 0.1, key=f"witt_{eid}")
        new_mtn = wc2.number_input("Klim/Aanval (MTN)", 0.0, 1.0, float(cw["MTN"]), 0.1, key=f"wmtn_{eid}")
        st.session_state.giro_weights_v2[eid] = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}

    som_input = new_spr + new_gc + new_itt + new_mtn
    active_w = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}
    if som_input > 0:
        active_w = {k: v / som_input for k, v in active_w.items()}
    else:
        active_w = {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}

    df_stage = bereken_alle_stage_scores(df, active_w)
    top_5 = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False]).head(5)
    top_5_namen = [f"{n} ({int(s)})" for n, s in top_5[['Naam', 'StageScore']].values]
    top_3_pure_names = top_5['Naam'].tolist()[:3]

    st.info(f"💡 **Suggesties Top 5:** {', '.join(top_5_namen)}")

    st.markdown("##### 🏁 Jouw Voorspelling (top 3)")
    if st.button("🤖 Suggesties Top 3 overnemen", key=f"auto_{eid}", use_container_width=True):
        for idx, naam in enumerate(top_3_pure_names):
            st.session_state.etappe_keuzes[eid][idx] = naam
        st.rerun()

    def get_display_name(naam):
        if naam == "-": return naam
        if naam in st.session_state.finaal_team: return f"⭐ {naam}"
        return naam

    def get_real_name(display_name):
        if display_name == "-": return None
        if display_name.startswith("⭐ "): return display_name[2:]
        return display_name

    renners_opties_stage_raw = ["-"] + df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False])['Naam'].tolist()
    renners_opties_stage = [get_display_name(r) for r in renners_opties_stage_raw]

    c1, c2, c3 = st.columns(3)
    for i, col in enumerate([c1, c2, c3]):
        current_val = st.session_state.etappe_keuzes[eid][i]
        display_val = get_display_name(current_val) if current_val else "-"
        d_idx = renners_opties_stage.index(display_val) if display_val in renners_opties_stage else 0
        keuze_display = col.selectbox(f"Positie {i+1}", renners_opties_stage, index=d_idx, key=f"sel_{eid}_{i}")
        st.session_state.etappe_keuzes[eid][i] = get_real_name(keuze_display)

    st.divider()
    st.markdown("##### 🎖️ Kopman — dubbele punten (x2)")

    if huidig_team_namen:
        auto_kopman = bepaal_auto_kopman(huidig_team_namen, etappe["id"], df)
        auto_hint   = f"Auto ({auto_kopman})" if auto_kopman else "Auto (geen team)"
    else:
        auto_kopman = None
        auto_hint   = "Auto (stel eerst een team in via Kolom 3 om Auto te gebruiken)"

    kopman_opties = ["🤖 " + auto_hint] + sorted(df['Naam'].tolist())
    huidige_keuze = st.session_state.kopman_keuzes.get(eid)
    kopman_idx    = kopman_opties.index(huidige_keuze) if huidige_keuze and huidige_keuze in kopman_opties else 0

    gekozen = st.selectbox(
        "Kopman voor deze etappe:",
        options=kopman_opties,
        index=kopman_idx,
        key=f"kopman_sel_{eid}",
        help="'Auto' = best scorende renner in je team."
    )

    if gekozen.startswith("🤖"):
        st.session_state.kopman_keuzes[eid] = None
        if auto_kopman:
            st.success(f"Automatische kopman: **{auto_kopman}**")
    else:
        st.session_state.kopman_keuzes[eid] = gekozen
        if huidig_team_namen and gekozen not in huidig_team_namen:
            st.warning(f"⚠️ Let op: **{gekozen}** zit (nog) niet in je definitieve team van 16!")
        else:
            st.success(f"Handmatige kopman: **{gekozen}**")

# Right Column: "Always-On" Team Tracker
with col_team:
    with st.container(border=True):
        st.subheader("🛡️ Mijn Team")

        c_renners, c_budget = st.columns(2)
        c_renners.metric("Renners", f"{aantal_renners} / 16")
        c_budget.metric("Budget", f"€ {100 - totaal_prijs:.1f}M")

        if st.button("🤖 Bereken Optimaal Team", use_container_width=True):
            draft_data = []
            for e_id, keuzes in st.session_state.etappe_keuzes.items():
                for i, r in enumerate(keuzes):
                    if r and r != "-":
                        draft_data.append({"Naam": r, "Punten": 3 - i})
            draft_df = pd.DataFrame(draft_data)
            draft_counts = {}
            if not draft_df.empty:
                draft_counts = dict(zip(
                    draft_df.groupby("Naam")["Punten"].sum().index,
                    draft_df.groupby("Naam")["Punten"].sum().values
                ))

            with st.spinner("Team berekenen..."):
                res = solve_giro_team(df, draft_counts=draft_counts, max_bud=100.0, max_ren=16, ev_column="EV")
                if res:
                    st.session_state.finaal_team = res
                    st.rerun()
                else:
                    st.error("Kon geen geldig team berekenen.")

        def update_finaal_team():
            st.session_state.finaal_team = st.session_state._finaal_team_selector_m

        def format_rider(naam):
            if naam not in df['Naam'].values: return naam
            r = df[df['Naam'] == naam].iloc[0]
            return f"{naam} - €{r['Prijs']}M"

        st.multiselect(
            "Selecteer 16 renners:",
            options=df['Naam'].tolist(),
            default=st.session_state.finaal_team,
            max_selections=16,
            key="_finaal_team_selector_m",
            on_change=update_finaal_team,
            format_func=format_rider,
            label_visibility="collapsed"
        )

        if huidig_team_namen:
            st.markdown("**Huidige Selectie:**")
            st.dataframe(huidig_team_df[['Naam', 'Type', 'Prijs']].sort_values('Prijs', ascending=False), hide_index=True, use_container_width=True)

            if st.button("🗑️ Wis Team", use_container_width=True):
                st.session_state.finaal_team = []
                st.rerun()
