import streamlit as st
import pandas as pd
import unicodedata
import os
import base64
import pulp
from app_utils.db import init_connection
from app_utils.giro_data import load_giro_data, calculate_giro_ev
from app_utils.giro_solver import solve_giro_team

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
st.title("✂️ Concept 3: Split View (Planning vs Execution)")
st.markdown("*Data en Statistieken van [Wielerorakel](https://wielerorakel.nl/)*")

with st.expander("ℹ️ Hoe werkt deze tool?"):
    st.markdown("""
    Deze tool gebruikt een **Split View Layout** met twee hoofdtabs:
    1. **🏗️ Planning & Selectie:** Voorspel eerst de etappes door ze bovenaan te selecteren, wegingen in te stellen en de top 3 en kopman te voorspellen. Scrol daarna naar beneden om handmatig je 16 renners te selecteren of het optimale team te berekenen.
    2. **📅 De Koers (Executie):** Na het selecteren van je team, bekijk je in deze tab het complete overzicht van je dagelijkse opstellingen en kopmannen.
    """)

if df.empty:
    st.error("Databestanden niet gevonden.")
    st.stop()

tab_plan, tab_exec = st.tabs(["🏗️ Planning & Selectie", "📅 De Koers (Executie)"])

with tab_plan:
    st.markdown("### 1. Etappes Voorspellen")

    # Horizontal Navigation
    if "aktieve_etappe_idx" not in st.session_state: st.session_state.aktieve_etappe_idx = 0

    nav_cols = st.columns(7)
    for i in range(21):
        col_idx = i % 7
        e = GIRO_ETAPPES[i]
        eid_str = str(e["id"])
        is_filled = len([k for k in st.session_state.etappe_keuzes.get(eid_str, []) if k]) > 0
        btn_label = f"{'🟢' if is_filled else '⚪'} E{e['id']}"
        btn_type = "primary" if st.session_state.aktieve_etappe_idx == i else "secondary"
        if nav_cols[col_idx].button(btn_label, key=f"nav_h_{i}", use_container_width=True, type=btn_type):
            st.session_state.aktieve_etappe_idx = i
            st.rerun()

    # Active Stage
    etappe = GIRO_ETAPPES[st.session_state.aktieve_etappe_idx]
    eid    = str(etappe["id"])
    cw     = st.session_state.giro_weights_v2[eid]

    st.divider()
    c_stage_left, c_stage_right = st.columns([1, 2])

    with c_stage_left:
        st.subheader(f"E{etappe['id']}: {etappe['route']}")
        st.caption(f"{etappe['type']} - {etappe['date']}")

        giro_link = "https://www.giroditalia.it/en/the-route/"
        prof_path = f"data/giro262/giro26-{etappe['id']}-hp.jpg"
        st.markdown(get_clickable_image_html(prof_path, f"Profiel+{etappe['id']}", giro_link), unsafe_allow_html=True)

        new_spr = st.number_input("SPR", 0.0, 1.0, float(cw["SPR"]), 0.1, key=f"wspr_{eid}")
        new_gc  = st.number_input("GC",  0.0, 1.0, float(cw["GC"]),  0.1, key=f"wgc_{eid}")
        new_itt = st.number_input("ITT", 0.0, 1.0, float(cw["ITT"]), 0.1, key=f"witt_{eid}")
        new_mtn = st.number_input("MTN", 0.0, 1.0, float(cw["MTN"]), 0.1, key=f"wmtn_{eid}")
        st.session_state.giro_weights_v2[eid] = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}

    with c_stage_right:
        som_input = new_spr + new_gc + new_itt + new_mtn
        active_w = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn} if som_input > 0 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
        active_w = {k: v / (som_input or 1) for k, v in active_w.items()}
        df_stage = bereken_alle_stage_scores(df, active_w)

        top_5 = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False]).head(5)
        st.info(f"💡 **Top 5 Suggesties:** {', '.join([f'{n} ({int(s)})' for n, s in top_5[['Naam', 'StageScore']].values])}")

        top_3_pure_names = top_5['Naam'].tolist()[:3]
        if st.button("🤖 Top 3 overnemen", key=f"auto_{eid}", use_container_width=True):
            for idx, naam in enumerate(top_3_pure_names): st.session_state.etappe_keuzes[eid][idx] = naam
            st.rerun()

        def get_real_name(display_name): return None if display_name == "-" else display_name
        renners_opties = ["-"] + df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False])['Naam'].tolist()

        c1, c2, c3 = st.columns(3)
        for i, col in enumerate([c1, c2, c3]):
            cur = st.session_state.etappe_keuzes[eid][i]
            idx = renners_opties.index(cur) if cur in renners_opties else 0
            val = col.selectbox(f"Positie {i+1}", renners_opties, index=idx, key=f"sel_{eid}_{i}")
            st.session_state.etappe_keuzes[eid][i] = get_real_name(val)

        kopman_opties = ["🤖 Auto"] + sorted(df['Naam'].tolist())
        cur_kopman = st.session_state.kopman_keuzes.get(eid)
        k_idx = kopman_opties.index(cur_kopman) if cur_kopman in kopman_opties else 0

        gekozen_k = st.selectbox("Kopman:", kopman_opties, index=k_idx, key=f"kop_{eid}")
        st.session_state.kopman_keuzes[eid] = None if gekozen_k == "🤖 Auto" else gekozen_k

    st.markdown("---")
    st.markdown("### 2. Team Selectie (16 Renners)")

    col_metrics, col_btn = st.columns([2, 1])
    col_metrics.write(f"**Renners:** {aantal_renners} / 16 | **Budget Over:** €{100 - totaal_prijs:.1f}M")
    if col_btn.button("🤖 Bereken Optimaal Team", use_container_width=True):
        draft_data = [{"Naam": r, "Punten": 3 - i} for e_id, keuzes in st.session_state.etappe_keuzes.items() for i, r in enumerate(keuzes) if r and r != "-"]
        draft_df = pd.DataFrame(draft_data)
        draft_counts = dict(zip(draft_df.groupby("Naam")["Punten"].sum().index, draft_df.groupby("Naam")["Punten"].sum().values)) if not draft_df.empty else {}

        with st.spinner("Team berekenen..."):
            res = solve_giro_team(df, draft_counts=draft_counts, max_bud=100.0, max_ren=16, ev_column="EV")
            if res:
                st.session_state.finaal_team = res
                st.rerun()

    def update_finaal_team(): st.session_state.finaal_team = st.session_state._finaal_team_split
    st.multiselect(
        "Mijn Team:",
        options=df['Naam'].tolist(),
        default=st.session_state.finaal_team,
        max_selections=16,
        key="_finaal_team_split",
        on_change=update_finaal_team,
        label_visibility="collapsed"
    )

with tab_exec:
    st.markdown("### Dagelijkse Opstellingen")
    if not huidig_team_namen:
        st.warning("Selecteer eerst een team in de Planning tab.")
    else:
        matrix_data = {renner: {"Renner": renner} for renner in st.session_state.finaal_team}
        for etappe in GIRO_ETAPPES:
            eid = str(etappe["id"])
            col_name = f"E{etappe['id']}"
            for renner in st.session_state.finaal_team:
                matrix_data[renner][col_name] = "-"

            cw = st.session_state.giro_weights_v2[eid]
            w = cw if sum(cw.values()) > 0 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
            team_stage_df = bereken_alle_stage_scores(huidig_team_df, w)

            top_9 = team_stage_df.sort_values('StageScore', ascending=False).head(9)['Naam'].tolist()
            handmatig_km = st.session_state.kopman_keuzes.get(eid)
            effectief_km = handmatig_km if handmatig_km in top_9 else (top_9[0] if top_9 else None)

            for renner in top_9:
                matrix_data[renner][col_name] = "©" if renner == effectief_km else "✅"

        st.dataframe(pd.DataFrame(list(matrix_data.values())), hide_index=True, use_container_width=True)
