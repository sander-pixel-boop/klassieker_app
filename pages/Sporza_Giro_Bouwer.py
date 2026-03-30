import streamlit as st
import pandas as pd
import json
import unicodedata
import os
import base64
import pulp
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
    bestand = "giro262/profile_score.csv"
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
        except Exception:
            pass

laad_profiel_scores()

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

def bereken_stage_scores(df, weights):
    """Geeft dict {renner: stagescore} op basis van wegingen."""
    s = sum(weights.values()) or 1.0
    w = {k: v / s for k, v in weights.items()}
    scores = {}
    for _, row in df.iterrows():
        scores[row['Naam']] = (
            row.get('SPR', 0) * w.get('SPR', 0) +
            row.get('GC',  0) * w.get('GC',  0) +
            row.get('ITT', 0) * w.get('ITT', 0) +
            row.get('MTN', 0) * w.get('MTN', 0)
        )
    return scores

def bepaal_auto_kopman(team_renners, etappe_id, df):
    """Berekent de automatische kopman puur op basis van het etappeprofiel."""
    w = next((e['w'] for e in GIRO_ETAPPES if e['id'] == etappe_id), {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25})
    s = sum(w.values()) or 1.0
    w = {k: v / s for k, v in w.items()}
    best, best_score = None, -1
    for r in team_renners:
        rij = df[df['Naam'] == r]
        if rij.empty: continue
        score = (
            rij.iloc[0].get('SPR', 0) * w.get('SPR', 0) +
            rij.iloc[0].get('GC',  0) * w.get('GC',  0) +
            rij.iloc[0].get('ITT', 0) * w.get('ITT', 0) +
            rij.iloc[0].get('MTN', 0) * w.get('MTN', 0)
        )
        if score > best_score:
            best_score = score
            best = r
    return best

def solve_final_team(df, draft_counts, max_bud=100.0, max_ren=16):
    prob = pulp.LpProblem("Giro_Builder", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("Select", df.index, cat='Binary')
    df_solve = df.copy()
    df_solve['Draft_Pts'] = df_solve['Naam'].map(draft_counts).fillna(0)
    df_solve['Obj_Score'] = (df_solve['Draft_Pts'] * 1000) + df_solve['EV']
    prob += pulp.lpSum([df_solve.loc[i, 'Obj_Score'] * x[i] for i in df_solve.index])
    prob += pulp.lpSum([x[i] for i in df_solve.index]) == max_ren
    prob += pulp.lpSum([df_solve.loc[i, 'Prijs'] * x[i] for i in df_solve.index]) <= max_bud
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))
    if pulp.LpStatus[prob.status] == 'Optimal':
        return [df_solve.loc[i, 'Naam'] for i in df_solve.index if x[i].varValue > 0.5]
    return []

@st.cache_data
def load_all_data():
    prijzen_file = "giro262/sporza_giro26_startlijst.csv"
    stats_file   = "renners_stats.csv"
    if not os.path.exists(prijzen_file) or not os.path.exists(stats_file):
        return pd.DataFrame()
    df_p = pd.read_csv(prijzen_file, sep=None, engine='python')
    df_s = pd.read_csv(stats_file,   sep=None, engine='python')
    df_p.columns = df_p.columns.str.strip()
    df_s.columns = df_s.columns.str.strip()
    naam_col_p = 'Naam' if 'Naam' in df_p.columns else 'Renner'
    naam_col_s = 'Naam' if 'Naam' in df_s.columns else 'Renner'
    df = pd.merge(df_p, df_s, left_on=naam_col_p, right_on=naam_col_s, how='left')
    df['Prijs'] = pd.to_numeric(df['Prijs'], errors='coerce').fillna(0)
    df.loc[df['Prijs'] > 1000, 'Prijs'] = df['Prijs'] / 1000000
    df.loc[df['Prijs'] == 0.8, 'Prijs'] = 0.75
    for col in ['GC', 'SPR', 'ITT', 'MTN']:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    df['EV'] = ((df['GC']/100)**4 * 400 + (df['SPR']/100)**4 * 250 +
                (df['ITT']/100)**4 * 80  + (df['MTN']/100)**4 * 100).fillna(0).round(0)
    # Zorg voor consistente Naam kolom
    if naam_col_p != 'Naam': df = df.rename(columns={naam_col_p: 'Naam'})
    elif 'Renner' in df.columns and 'Naam' not in df.columns: df = df.rename(columns={'Renner': 'Naam'})
    return df.drop_duplicates(subset=['Naam']).sort_values('Naam')

df = load_all_data()

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
st.title("🇮🇹 Handmatige Team Bouwer")
st.markdown("*Data en Statistieken van [Wielerorakel](https://wielerorakel.nl/)*")

if df.empty:
    st.error("Databestanden niet gevonden.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Etappe Voorspellingen",
    "🛡️ Finaal Team Samenstellen",
    "🚀 Opstellingen & Kopmannen",
    "📋 Startlijst",
    "ℹ️ Uitleg"
])

# ══════════════════════════════════════════════════════════════════════
# TAB 1 – ETAPPE VOORSPELLINGEN + KOPMAN PER ETAPPE
# ══════════════════════════════════════════════════════════════════════
with tab1:
    # ── Etappe navigator ─────────────────────────────────────────────
    # Persist which stage is active across reruns
    if "aktieve_etappe_idx" not in st.session_state:
        st.session_state.aktieve_etappe_idx = 0

    # Build a quick progress summary for the mini-table above the nav
    def etappe_samenvatting(eid_str):
        keuzes   = [k for k in st.session_state.etappe_keuzes.get(eid_str, []) if k]
        kopman   = st.session_state.kopman_keuzes.get(eid_str)
        n_picks  = len(keuzes)
        km_badge = f"🎖️ {kopman}" if kopman else "🤖 Auto"
        return n_picks, km_badge

    # Top nav: previous / stage selector / next / auto-fill
    nav_left, nav_mid, nav_right, nav_auto = st.columns([1, 4, 1, 2])
    with nav_left:
        if st.button("◀ Vorige", use_container_width=True, disabled=st.session_state.aktieve_etappe_idx == 0):
            st.session_state.aktieve_etappe_idx -= 1
            st.rerun()
    with nav_right:
        if st.button("Volgende ▶", use_container_width=True, disabled=st.session_state.aktieve_etappe_idx == len(GIRO_ETAPPES) - 1):
            st.session_state.aktieve_etappe_idx += 1
            st.rerun()
    with nav_mid:
        etappe_labels = [
            f"E{e['id']} – {e['route']} ({e['type']})" for e in GIRO_ETAPPES
        ]
        gekozen_label = st.selectbox(
            "Kies etappe:",
            options=etappe_labels,
            index=st.session_state.aktieve_etappe_idx,
            label_visibility="collapsed",
        )
        nieuw_idx = etappe_labels.index(gekozen_label)
        if nieuw_idx != st.session_state.aktieve_etappe_idx:
            st.session_state.aktieve_etappe_idx = nieuw_idx
            st.rerun()
    with nav_auto:
        if st.button("🪄 Vul alles met suggesties", use_container_width=True, help="Overschrijft alle huidige keuzes met de gesuggereerde Top 3 per etappe"):
            for e in GIRO_ETAPPES:
                eid_str = str(e["id"])
                cw = st.session_state.giro_weights_v2[eid_str]

                som_input = sum(cw.values())
                w = {k: v / som_input for k, v in cw.items()} if som_input > 0 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}

                df_stage = df.copy()
                df_stage['StageScore'] = (
                    df_stage['SPR'] * w['SPR'] +
                    df_stage['GC']  * w['GC']  +
                    df_stage['ITT'] * w['ITT']  +
                    df_stage['MTN'] * w['MTN']
                )
                top_3_pure_names = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False])['Naam'].tolist()[:3]
                for idx, naam in enumerate(top_3_pure_names):
                    st.session_state.etappe_keuzes[eid_str][idx] = naam
                    # Forceer de streamlite UI selectbox cache om ook deze waarde aan te nemen
                    st.session_state[f"sel_{eid_str}_{idx}"] = naam
            st.rerun()

    # ── Mini progress bar: all 21 stages as coloured dots ────────────
    dots = []
    for e in GIRO_ETAPPES:
        eid_dot = e["id"]
        n, _ = etappe_samenvatting(str(eid_dot))
        active = eid_dot == GIRO_ETAPPES[st.session_state.aktieve_etappe_idx]["id"]
        if active:
            dots.append(f"<span title='E{eid_dot}' style='font-size:18px;cursor:default;'>🔵</span>")
        elif n > 0:
            dots.append(f"<span title='E{eid_dot} – {n} picks' style='font-size:18px;cursor:default;'>🟢</span>")
        else:
            dots.append(f"<span title='E{eid_dot} – geen picks' style='font-size:18px;cursor:default;'>⚪</span>")
    st.markdown(" ".join(dots) + "  <small style='color:grey;'>🔵 actief &nbsp; 🟢 ingevuld &nbsp; ⚪ leeg</small>", unsafe_allow_html=True)
    st.markdown("---", unsafe_allow_html=True) # more compact line

    # ── Active stage editor ───────────────────────────────────────────
    etappe = GIRO_ETAPPES[st.session_state.aktieve_etappe_idx]
    eid    = str(etappe["id"])
    cw     = st.session_state.giro_weights_v2[eid]
    n_picks, km_badge = etappe_samenvatting(eid)

    # Use a two-column layout to make it more compact
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        # Header & Meta
        st.subheader(f"E{etappe['id']}: {etappe['route']}")
        col_meta1, col_meta2 = st.columns(2)
        col_meta1.metric("Type",    etappe["type"])
        col_meta2.metric("Datum",   etappe["date"])

        # Route & profile images
        giro_link = "https://www.giroditalia.it/en/the-route/"
        map_path  = f"giro262/giro26-{etappe['id']}-map.jpg"
        prof_path = f"giro262/giro26-{etappe['id']}-hp.jpg"
        i1, i2 = st.columns(2)
        i1.markdown(get_clickable_image_html(map_path,  f"Kaart+{etappe['id']}", giro_link), unsafe_allow_html=True)
        i2.markdown(get_clickable_image_html(prof_path, f"Profiel+{etappe['id']}", giro_link), unsafe_allow_html=True)

        # ── Weging ───────────────────────────────────────────────────────
        st.markdown("##### ⚙️ Etappeprofiel weging")
        wc1, wc2, wc3, wc4 = st.columns(4)
        new_spr = wc1.number_input("SPR",      0.0, 1.0, float(cw["SPR"]), 0.1, key=f"wspr_{eid}")
        new_gc  = wc2.number_input("GC",       0.0, 1.0, float(cw["GC"]),  0.1, key=f"wgc_{eid}")
        new_itt = wc3.number_input("ITT",      0.0, 1.0, float(cw["ITT"]), 0.1, key=f"witt_{eid}")
        new_mtn = wc4.number_input("MTN",      0.0, 1.0, float(cw["MTN"]), 0.1, key=f"wmtn_{eid}")
        st.session_state.giro_weights_v2[eid] = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}

        som_input = new_spr + new_gc + new_itt + new_mtn
        if abs(som_input - 1.0) > 0.01 and som_input > 0:
            st.caption(f"ℹ️ Wordt automatisch herschaald naar 100%.")
            active_w = {k: v / som_input for k, v in {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}.items()}
        elif som_input == 0:
            st.error("Weging mag niet 0% zijn.")
            active_w = {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
        else:
            active_w = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}

    with col_right:
        # ── Suggesties ─────────────────────────────────────────────────
        df_stage = df.copy()
        df_stage['StageScore'] = (
            df_stage['SPR'] * active_w['SPR'] +
            df_stage['GC']  * active_w['GC']  +
            df_stage['ITT'] * active_w['ITT']  +
            df_stage['MTN'] * active_w['MTN']
        )
        top_5            = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False]).head(5)
        top_5_namen      = [f"{row['Naam']} ({int(row['StageScore'])})" for _, row in top_5.iterrows()]
        top_3_pure_names = top_5['Naam'].tolist()[:3]

        st.markdown("##### 💡 Top 5 Suggesties")
        st.info(", ".join(top_5_namen))

        # ── Voorspelling ─────────────────────────────────────────────────
        sorteer_optie = st.radio(
            "Sorteer keuzelijst op:",
            ["🔤 Alfabetisch", "📊 Etappe Score"],
            horizontal=True,
            key="sorteer_tab1"
        )
        if "Alfabetisch" in sorteer_optie:
            renners_opties_stage = ["-"] + sorted(df['Naam'].tolist())
        else:
            renners_opties_stage = ["-"] + df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False])['Naam'].tolist()

        pred_head, pred_btn = st.columns([1, 1])
        with pred_head:
            st.markdown("##### 🏁 Jouw Voorspelling")
        with pred_btn:
            if st.button("🤖 Top 3 overnemen", use_container_width=True):
                for idx, naam in enumerate(top_3_pure_names):
                    st.session_state.etappe_keuzes[eid][idx] = naam
                    # Forceer de streamlite UI selectbox cache om ook deze waarde aan te nemen
                    st.session_state[f"sel_{eid}_{idx}"] = naam
                st.rerun()

        c1, c2, c3 = st.columns(3)
        for i, col in enumerate([c1, c2, c3]):
            current_val = st.session_state.etappe_keuzes[eid][i]
            d_idx = renners_opties_stage.index(current_val) if current_val in renners_opties_stage else 0
            keuze = col.selectbox(f"Positie {i+1}", renners_opties_stage, index=d_idx, key=f"sel_{eid}_{i}", label_visibility="collapsed")
            st.session_state.etappe_keuzes[eid][i] = keuze if keuze != "-" else None

        # ── Kopman ───────────────────────────────────────────────────────
        st.markdown(f"##### 🎖️ Kopman (Actueel: {km_badge})")

        if huidig_team_namen:
            auto_kopman = bepaal_auto_kopman(huidig_team_namen, etappe["id"], df)
            auto_hint   = f"Auto ({auto_kopman})" if auto_kopman else "Auto (geen team)"
        else:
            auto_kopman = None
            auto_hint   = "Auto (stel eerst team in)"

        kopman_opties = ["🤖 " + auto_hint] + sorted(huidig_team_namen)
        huidige_keuze = st.session_state.kopman_keuzes.get(eid)
        kopman_idx    = kopman_opties.index(huidige_keuze) if huidige_keuze and huidige_keuze in kopman_opties else 0

        gekozen = st.selectbox(
            "Kopman voor deze etappe:",
            options=kopman_opties,
            index=kopman_idx,
            key=f"kopman_sel_{eid}",
            label_visibility="collapsed"
        )

        if gekozen.startswith("🤖"):
            st.session_state.kopman_keuzes[eid] = None
            if auto_kopman:
                st.caption(f"Automatische kopman: **{auto_kopman}**")
        else:
            st.session_state.kopman_keuzes[eid] = gekozen
            st.caption(f"Handmatige kopman: **{gekozen}**")

# ══════════════════════════════════════════════════════════════════════
# TAB 2 – FINAAL TEAM SAMENSTELLEN
# ══════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("1. Jouw Voorspellingen Overzicht")
    st.write("Renners die je vaker voorspelt krijgen meer gewicht bij de automatische teamselectie.")

    draft_data = []
    for eid, keuzes in st.session_state.etappe_keuzes.items():
        for i, r in enumerate(keuzes):
            if r and r != "-":
                draft_data.append({"Naam": r, "Punten": 3 - i})

    draft_df     = pd.DataFrame(draft_data)
    draft_counts = {}
    if not draft_df.empty:
        draft_summary = (
            draft_df.groupby("Naam")["Punten"].sum()
            .reset_index()
            .sort_values(by="Punten", ascending=False)
        )
        draft_summary = pd.merge(draft_summary, df[['Naam', 'Prijs', 'EV']], on='Naam', how='left')
        st.dataframe(draft_summary, hide_index=True, use_container_width=True)
        draft_counts = dict(zip(draft_summary['Naam'], draft_summary['Punten']))
    else:
        st.info("Je hebt nog geen etappes voorspeld in Tab 1.")

    st.divider()
    st.subheader("2. Finaal Team Selecteren (16 Renners)")

    c_auto, c_space = st.columns([1, 2])
    with c_auto:
        if st.button("🤖 Bereken Optimaal Team", type="primary", use_container_width=True):
            res = solve_final_team(df, draft_counts, 100.0, 16)
            if res:
                st.session_state.finaal_team = res
                st.rerun()
            else:
                st.error("Kon geen geldig team berekenen binnen het budget.")

    def update_finaal_team():
        st.session_state.finaal_team = st.session_state._finaal_team_selector

    st.multiselect(
        "Selecteer handmatig je 16 definitieve renners:",
        options=df['Naam'].tolist(),
        default=st.session_state.finaal_team,
        max_selections=16,
        key="_finaal_team_selector",
        on_change=update_finaal_team
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Aantal Renners", f"{aantal_renners} / 16")
    c2.metric("Budget Besteed",  f"€ {totaal_prijs:.2f}M")
    c3.metric("Budget Over",     f"€ {100 - totaal_prijs:.2f}M")

    st.divider()
    st.subheader("3. Jouw Definitieve Selectie")
    if not huidig_team_df.empty:
        col_grafiek, col_tabel = st.columns([1, 2])
        with col_grafiek:
            plot_cols = [c for c in ['GC', 'SPR', 'ITT', 'MTN'] if c in huidig_team_df.columns]
            if plot_cols:
                st.bar_chart(huidig_team_df[plot_cols].mean())
        with col_tabel:
            st.dataframe(
                huidig_team_df[['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV']].sort_values('Prijs', ascending=False),
                hide_index=True, use_container_width=True
            )
    else:
        st.info("Selecteer hierboven je team.")

# ══════════════════════════════════════════════════════════════════════
# TAB 3 – OPSTELLINGEN MATRIX + KOPMAN OVERZICHT
# ══════════════════════════════════════════════════════════════════════
with tab3:
    if not st.session_state.finaal_team:
        st.warning("Stel eerst een definitief team samen in Tab 2.")
    else:
        # ── Kopman Overzicht Tabel ────────────────────────────────────────
        st.subheader("🎖️ Kopman per Etappe – Overzicht")
        st.markdown(
            "Handmatig ingestelde kopmannen zijn gemarkeerd met **✏️**. "
            "Auto-kopmannen (op basis van etappeprofiel) zijn gemarkeerd met **🤖**."
        )

        kopman_overzicht = []
        for etappe in GIRO_ETAPPES:
            eid = str(etappe["id"])
            handmatig = st.session_state.kopman_keuzes.get(eid)
            auto_k    = bepaal_auto_kopman(huidig_team_namen, etappe["id"], df)

            if handmatig:
                effectief_kopman = handmatig
                bron = "✏️ Handmatig"
            else:
                effectief_kopman = auto_k
                bron = "🤖 Auto"

            kopman_overzicht.append({
                "E":      f"E{etappe['id']}",
                "Datum":  etappe["date"],
                "Route":  etappe["route"],
                "Type":   etappe["type"],
                "Kopman": effectief_kopman or "-",
                "Bron":   bron,
            })

        df_kopman_ovz = pd.DataFrame(kopman_overzicht)

        def kleur_kopman(row):
            if "Handmatig" in row["Bron"]:
                return ["background-color: rgba(255,215,0,0.15)"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df_kopman_ovz.style.apply(kleur_kopman, axis=1),
            hide_index=True,
            use_container_width=True
        )

        st.divider()

        # ── Opstellingen Matrix ───────────────────────────────────────────
        st.subheader("📅 Dagelijkse Opstellingen Matrix")
        st.write(
            "**©** = Kopman (dubbele punten) &nbsp;|&nbsp; "
            "**✅** = Basis &nbsp;|&nbsp; **-** = Bank"
        )

        matrix_data = {renner: {"Renner": renner} for renner in st.session_state.finaal_team}

        for etappe in GIRO_ETAPPES:
            eid      = str(etappe["id"])
            col_name = f"E{etappe['id']}"
            cw       = st.session_state.giro_weights_v2[eid]

            for renner in st.session_state.finaal_team:
                matrix_data[renner][col_name] = "-"

            voorspeld = [n for n in st.session_state.etappe_keuzes[eid] if n and n in st.session_state.finaal_team]
            som_input = sum(cw.values())
            w = {k: v / som_input for k, v in cw.items()} if som_input > 0 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}

            team_stage_df = huidig_team_df.copy()
            team_stage_df['StageScore'] = (
                team_stage_df.get('SPR', 0) * w['SPR'] +
                team_stage_df.get('GC',  0) * w['GC']  +
                team_stage_df.get('ITT', 0) * w['ITT']  +
                team_stage_df.get('MTN', 0) * w['MTN']
            )

            voorspeld_df = team_stage_df[team_stage_df['Naam'].isin(voorspeld)] if voorspeld else pd.DataFrame()
            rest_df      = team_stage_df[~team_stage_df['Naam'].isin(voorspeld)].sort_values('StageScore', ascending=False)
            top_9_df     = pd.concat([voorspeld_df, rest_df]).head(9)

            # Bepaal kopman voor deze etappe
            handmatig_km  = st.session_state.kopman_keuzes.get(eid)
            starters_lijst = top_9_df['Naam'].tolist()
            if handmatig_km and handmatig_km in starters_lijst:
                effectief_km = handmatig_km
            elif handmatig_km and handmatig_km not in starters_lijst:
                # Handmatig kopman zit niet in de 9 starters → waarschuwing
                effectief_km = handmatig_km  # toch tonen zodat gebruiker het ziet
            else:
                # Auto: eerste (hoogst scorende) starter
                effectief_km = starters_lijst[0] if starters_lijst else None

            for renner_naam in starters_lijst:
                matrix_data[renner_naam][col_name] = "©" if renner_naam == effectief_km else "✅"

        matrix_df_display = pd.DataFrame(list(matrix_data.values()))
        st.dataframe(matrix_df_display, hide_index=True, use_container_width=True)

        # ── Details per Etappe ────────────────────────────────────────────
        st.divider()
        st.subheader("🔍 Details per Etappe")

        for etappe in GIRO_ETAPPES:
            eid = str(etappe["id"])
            cw  = st.session_state.giro_weights_v2[eid]

            voorspeld    = [n for n in st.session_state.etappe_keuzes[eid] if n and n in st.session_state.finaal_team]
            som_input    = sum(cw.values())
            w = {k: v / som_input for k, v in cw.items()} if som_input > 0 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}

            team_stage_df = huidig_team_df.copy()
            team_stage_df['StageScore'] = (
                team_stage_df.get('SPR', 0) * w['SPR'] +
                team_stage_df.get('GC',  0) * w['GC']  +
                team_stage_df.get('ITT', 0) * w['ITT']  +
                team_stage_df.get('MTN', 0) * w['MTN']
            )
            voorspeld_df = team_stage_df[team_stage_df['Naam'].isin(voorspeld)] if voorspeld else pd.DataFrame()
            rest_df      = team_stage_df[~team_stage_df['Naam'].isin(voorspeld)].sort_values('StageScore', ascending=False)
            top_9_df     = pd.concat([voorspeld_df, rest_df]).head(9)
            starters_lijst = top_9_df['Naam'].tolist()

            handmatig_km = st.session_state.kopman_keuzes.get(eid)
            if handmatig_km and handmatig_km in starters_lijst:
                effectief_km = handmatig_km
                kopman_bron  = "✏️ Handmatig"
            elif handmatig_km and handmatig_km not in starters_lijst:
                effectief_km = handmatig_km
                kopman_bron  = "⚠️ Handmatig (staat niet in top 9!)"
            else:
                effectief_km = starters_lijst[0] if starters_lijst else None
                kopman_bron  = "🤖 Auto"

            with st.expander(
                f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']}) "
                f"| Kopman: **{effectief_km or '-'}** {kopman_bron}"
            ):
                # Waarschuwing als handmatige kopman buiten de starters valt
                if handmatig_km and handmatig_km not in starters_lijst:
                    st.warning(
                        f"⚠️ **{handmatig_km}** is je handmatige kopman maar staat niet in de top 9 starters "
                        f"voor deze etappe. Pas je etappevoorspellingen aan of kies een andere kopman."
                    )

                opstelling = []
                for _, row in top_9_df.iterrows():
                    naam = row['Naam']
                    if naam == effectief_km:
                        rol = f"© Kopman ({kopman_bron})"
                    elif naam in voorspeld:
                        rol = "Basis (Jouw Voorspelling)"
                    else:
                        rol = "Basis (Automatische Opvulling)"
                    opstelling.append({
                        "Rol":             rol,
                        "Renner":          naam,
                        "Verwachte Score": int(row['StageScore'])
                    })

                st.dataframe(pd.DataFrame(opstelling), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 4 – STARTLIJST
# ══════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Volledige Startlijst & Prijzen")
    cols_show = [c for c in ['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV'] if c in df.columns]
    st.dataframe(df[cols_show].sort_values('Prijs', ascending=False), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 5 – UITLEG
# ══════════════════════════════════════════════════════════════════════
with tab5:
    st.header("ℹ️ Uitleg & Disclaimer")

    st.warning("""
    **⚠️ LET OP: Voorlopige Data!**
    De huidige startlijst en prijzen zijn nog niet definitief.
    Zodra Sporza de officiële Giromanager lanceert, worden de bestanden geüpdatet.
    """)

    st.markdown("""
    ### 🎖️ Kopman – Hoe werkt het?

    In Sporza Giromanager kies je per etappe **één kopman** die dubbele punten scoort (x2).

    **Automatische kopman (🤖 Auto)**
    Het systeem kiest automatisch de renner uit jouw 9 starters die het beste past bij het
    etappeprofiel (sprint, klim, tijdrit of aanval). Dit is handig als je snel wil gaan.

    **Handmatige kopman (✏️ Handmatig)**
    In Tab 1 kun je per etappe zelf een kopman kiezen uit je 16 renners.
    De expander-header toont direct welke kopman actief is zodat je een snel overzicht hebt.

    > **Tip:** In Tab 3 zie je een volledig overzicht van alle kopmannen en krijg je een
    > waarschuwing als je handmatige kopman niet in de top 9 starters voor die etappe valt.

    ### 🛠️ Hoe werkt de Handmatige Bouwer?

    1. **Tab 1 – Voorspellingen:** Kies per etappe welke renners jij verwacht te scoren
       én stel je kopman in.
    2. **Tab 2 – Finaal Team:** Selecteer je definitieve 16 renners of laat het systeem ze
       automatisch kiezen op basis van jouw voorspellingen.
    3. **Tab 3 – Opstellingen:** Bekijk de dagelijkse 9-koppige opstelling plus
       een volledig kopman-overzicht voor alle 21 etappes.
    """)
