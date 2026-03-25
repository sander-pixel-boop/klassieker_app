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
st.set_page_config(page_title="Sporza Giro Team Bouwer", layout="wide", page_icon="🛠️")

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
    {"id": 1,  "date": "08/05", "route": "Nessebar - Burgas",                        "type": "Vlak",       "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 2,  "date": "09/05", "route": "Burgas - Valiko Tarnovo",                  "type": "Heuvel",     "w": {"SPR": 0.3, "GC": 0.3, "ITT": 0.0, "MTN": 0.4}},
    {"id": 3,  "date": "10/05", "route": "Plovdiv - Sofia",                          "type": "Vlak/Heuvel","w": {"SPR": 0.9, "GC": 0.0, "ITT": 0.0, "MTN": 0.1}},
    {"id": 4,  "date": "12/05", "route": "Catanzaro - Cosenza",                      "type": "Vlak/Heuvel","w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 5,  "date": "13/05", "route": "Praia a Mare - Potenza",                   "type": "Heuvel",     "w": {"SPR": 0.1, "GC": 0.6, "ITT": 0.0, "MTN": 0.3}},
    {"id": 6,  "date": "14/05", "route": "Paestum - Naples",                         "type": "Heuvel",     "w": {"SPR": 0.8, "GC": 0.0, "ITT": 0.0, "MTN": 0.2}},
    {"id": 7,  "date": "15/05", "route": "Formia - Blockhaus",                       "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 8,  "date": "16/05", "route": "Chieti - Fermo",                           "type": "Heuvel",     "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 9,  "date": "17/05", "route": "Cervia - Corno alle Scale",                "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.8, "ITT": 0.0, "MTN": 0.2}},
    {"id": 10, "date": "19/05", "route": "Viareggio - Massa",                        "type": "Tijdrit",    "w": {"SPR": 0.0, "GC": 0.0, "ITT": 1.0, "MTN": 0.0}},
    {"id": 11, "date": "20/05", "route": "Porcari - Chiavari",                       "type": "Heuvel",     "w": {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4}},
    {"id": 12, "date": "21/05", "route": "Imperia - Novi Ligure",                    "type": "Vlak",       "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 13, "date": "22/05", "route": "Alessandria - Verbania",                   "type": "Heuvel",     "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 14, "date": "23/05", "route": "Aosta - Pila",                             "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 15, "date": "24/05", "route": "Voghera - Milan",                          "type": "Vlak",       "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 16, "date": "26/05", "route": "Bellinzona - Carì",                        "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 17, "date": "27/05", "route": "Cassano d'Adda - Andalo",                  "type": "Heuvel",     "w": {"SPR": 0.1, "GC": 0.5, "ITT": 0.0, "MTN": 0.4}},
    {"id": 18, "date": "28/05", "route": "Fai della Paganella - Pieve di Soligo",    "type": "Heuvel",     "w": {"SPR": 0.3, "GC": 0.2, "ITT": 0.0, "MTN": 0.5}},
    {"id": 19, "date": "29/05", "route": "Feltre - Alleghe",                         "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 20, "date": "30/05", "route": "Gemona del Friuli - Piancavallo",          "type": "Berg",       "w": {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1}},
    {"id": 21, "date": "31/05", "route": "Rome - Rome",                              "type": "Vlak",       "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
]

TYPE_EMOJI = {
    "Vlak": "➖", "Heuvel": "↗️", "Vlak/Heuvel": "〰️",
    "Berg": "⛰️", "Tijdrit": "⏱️",
}

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
    stats_file = "renners_stats.csv"
    if not os.path.exists(prijzen_file) or not os.path.exists(stats_file):
        return pd.DataFrame()

    df_p = pd.read_csv(prijzen_file, sep=None, engine='python')
    df_s = pd.read_csv(stats_file, sep=None, engine='python')
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

    if naam_col_p != 'Naam': df = df.rename(columns={naam_col_p: 'Naam'})
    return df.sort_values('Naam')

df = load_all_data()

# --- SESSION STATE ---
if "etappe_keuzes"    not in st.session_state:
    st.session_state.etappe_keuzes    = {str(e["id"]): [None, None, None] for e in GIRO_ETAPPES}
if "giro_weights_v2"  not in st.session_state:
    st.session_state.giro_weights_v2  = {str(e["id"]): e["w"].copy() for e in GIRO_ETAPPES}
if "finaal_team"      not in st.session_state:
    st.session_state.finaal_team      = []

huidig_team_namen = st.session_state.finaal_team
huidig_team_df    = df[df['Naam'].isin(huidig_team_namen)].copy() if not df.empty else pd.DataFrame()
totaal_prijs      = huidig_team_df['Prijs'].sum() if not huidig_team_df.empty else 0
aantal_renners    = len(huidig_team_namen)

# --- SIDEBAR ---
with st.sidebar:
    st.title("📋 Jouw Team")

    # Budget & renners meter
    budget_over = 100 - totaal_prijs
    budget_pct  = min(totaal_prijs / 100, 1.0)
    st.progress(budget_pct, text=f"€ {totaal_prijs:.2f}M / €100M")

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Budget over", f"€ {budget_over:.2f}M",
                  delta_color="inverse" if budget_over < 0 else "normal")
    col_m2.metric("Renners", f"{aantal_renners} / 16",
                  delta_color="inverse" if aantal_renners > 16 else "normal")

    if aantal_renners > 16: st.error("🚨 Te veel renners!")
    if totaal_prijs > 100:  st.error("🚨 Budget overschreden!")

    st.divider()

    if st.button("💾 Opslaan", type="primary", use_container_width=True):
        data = {
            "team":          st.session_state.finaal_team,
            "etappe_keuzes": st.session_state.etappe_keuzes,
            "weights":       st.session_state.giro_weights_v2
        }
        supabase.table(TABEL_NAAM).update({DB_KOLOM: data}).eq("username", speler_naam).execute()
        st.success("Opgeslagen!")

    if st.button("🔄 Inladen", use_container_width=True):
        res = supabase.table(TABEL_NAAM).select(DB_KOLOM).eq("username", speler_naam).execute()
        if res.data and res.data[0].get(DB_KOLOM):
            db_data = res.data[0][DB_KOLOM]
            st.session_state.etappe_keuzes   = db_data.get("etappe_keuzes", {str(e["id"]): [None]*3 for e in GIRO_ETAPPES})
            st.session_state.giro_weights_v2 = db_data.get("weights", {str(e["id"]): e["w"].copy() for e in GIRO_ETAPPES})
            st.session_state.finaal_team     = db_data.get("team", [])
            st.rerun()

    # Compact teamlijst in sidebar
    if huidig_team_namen:
        st.divider()
        st.caption("Geselecteerde renners:")
        for r in sorted(huidig_team_namen):
            prijs = df.loc[df['Naam'] == r, 'Prijs'].values
            p_str = f"€{prijs[0]:.1f}M" if len(prijs) > 0 else ""
            st.caption(f"• {r} {p_str}")

# --- HOOFDSCHERM ---
st.title("🛠️ Giro Team Bouwer")
st.markdown(
    "Bouw je team op etappe voor etappe. Kies renners die jij ziet scoren, "
    "laat de assistent de rest aanvullen en stel je definitieve 16 samen. "
    "*Data van [Wielerorakel](https://wielerorakel.nl/)*"
)

if df.empty:
    st.error("Databestanden niet gevonden. Controleer de mappen.")
    st.stop()

# Progress overzicht bovenaan
n_etappes_met_picks = sum(
    1 for eid in st.session_state.etappe_keuzes
    if any(x for x in st.session_state.etappe_keuzes[eid] if x)
)
col_p1, col_p2, col_p3 = st.columns(3)
col_p1.metric("Etappes ingevuld", f"{n_etappes_met_picks} / 21")
col_p2.metric("Renners in team",  f"{aantal_renners} / 16")
col_p3.metric("Budget besteed",   f"€ {totaal_prijs:.2f}M")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Etappe Picks",
    "🛡️ Team Samenstellen",
    "🚀 Opstellingen",
    "📋 Startlijst",
    "ℹ️ Uitleg"
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1: ETAPPE PICKS
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.info(
        "Kies per etappe welke renners jij ziet winnen of hoog eindigen. "
        "De assistent suggereert kandidaten op basis van het profiel — jij beslist. "
        "Jouw picks worden in Tab 2 gebruikt om het definitieve team samen te stellen."
    )

    sorteer_optie = st.radio(
        "Sorteer dropdowns op:", ["🔤 Alfabetisch", "📊 Verwachte Waarde (per etappe)"],
        horizontal=True
    )

    for etappe in GIRO_ETAPPES:
        eid  = str(etappe["id"])
        cw   = st.session_state.giro_weights_v2[eid]
        emoji = TYPE_EMOJI.get(etappe["type"], "")

        som_header = sum(cw.values()) if sum(cw.values()) > 0 else 1.0
        weight_str = (
            f"SPR:{int((cw['SPR']/som_header)*100)}% "
            f"GC:{int((cw['GC']/som_header)*100)}% "
            f"ITT:{int((cw['ITT']/som_header)*100)}% "
            f"MTN:{int((cw['MTN']/som_header)*100)}%"
        )

        huidige = [x for x in st.session_state.etappe_keuzes[eid] if x]
        picks_str = f"✅ Jouw keuze: {', '.join(huidige)}" if huidige else "⏳ Nog geen keuze"

        with st.expander(f"**E{etappe['id']}** {emoji} {etappe['route']} ({etappe['date']})"):
            st.caption(picks_str)
            
            # Afbeeldingen
            giro_link = "https://www.giroditalia.it/en/the-route/"
            map_path  = f"giro262/giro26-{etappe['id']}-map.jpg"
            prof_path = f"giro262/giro26-{etappe['id']}-hp.jpg"
            i1, i2 = st.columns(2)
            i1.markdown(get_clickable_image_html(map_path,  f"Kaart+{etappe['id']}", giro_link), unsafe_allow_html=True)
            i2.markdown(get_clickable_image_html(prof_path, f"Profiel+{etappe['id']}", giro_link), unsafe_allow_html=True)

            st.divider()

            # Weging sliders
            st.markdown("###### ⚙️ Profiel weging aanpassen:")
            wc1, wc2, wc3, wc4 = st.columns(4)
            new_spr = wc1.number_input("Sprint",       0.0, 1.0, float(cw["SPR"]), 0.1, key=f"wspr_{eid}")
            new_gc  = wc2.number_input("Klassement",   0.0, 1.0, float(cw["GC"]),  0.1, key=f"wgc_{eid}")
            new_itt = wc3.number_input("Tijdrit",      0.0, 1.0, float(cw["ITT"]), 0.1, key=f"witt_{eid}")
            new_mtn = wc4.number_input("Klim/Aanval",  0.0, 1.0, float(cw["MTN"]), 0.1, key=f"wmtn_{eid}")
            st.session_state.giro_weights_v2[eid] = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}

            som_input = new_spr + new_gc + new_itt + new_mtn
            if abs(som_input - 1.0) > 0.01 and som_input > 0:
                st.warning(f"⚠️ Weging telt op tot {som_input*100:.0f}% — wordt automatisch herschaald.")
                active_weights = {"SPR": new_spr/som_input, "GC": new_gc/som_input,
                                  "ITT": new_itt/som_input, "MTN": new_mtn/som_input}
            elif som_input == 0:
                st.error("⚠️ Weging mag niet 0% zijn.")
                active_weights = {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
            else:
                active_weights = st.session_state.giro_weights_v2[eid]

            # Assistent suggesties
            df_stage = df.copy()
            df_stage['StageScore'] = (
                df_stage['SPR'] * active_weights['SPR'] +
                df_stage['GC']  * active_weights['GC']  +
                df_stage['ITT'] * active_weights['ITT'] +
                df_stage['MTN'] * active_weights['MTN']
            )
            top_5 = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False]).head(5)
            top_5_namen = [f"{row['Naam']} ({int(row['StageScore'])})" for _, row in top_5.iterrows()]
            top_3_pure  = top_5['Naam'].tolist()[:3]

            st.info(f"💡 **Assistent tip:** {', '.join(top_5_namen)}")

            # Jouw picks
            if "Alfabetisch" in sorteer_optie:
                renners_opties = ["-"] + sorted(df['Naam'].tolist())
            else:
                renners_opties = ["-"] + df_stage.sort_values(
                    by=['StageScore', 'EV'], ascending=[False, False])['Naam'].tolist()

            pick_head, pick_btn = st.columns([3, 1])
            pick_head.markdown("###### ✏️ Jouw keuze (max 3):")
            if pick_btn.button("🤖 Neem top 3 over", key=f"btn_ai_{eid}"):
                for idx, naam in enumerate(top_3_pure):
                    st.session_state.etappe_keuzes[eid][idx] = naam
                    st.session_state[f"sel_{eid}_{idx}"] = naam
                st.rerun()

            c1, c2, c3 = st.columns(3)
            for i, col in enumerate([c1, c2, c3]):
                current_val = st.session_state.etappe_keuzes[eid][i]
                d_idx = renners_opties.index(current_val) if current_val in renners_opties else 0
                keuze = col.selectbox(f"Pos {i+1}", renners_opties, index=d_idx, key=f"sel_{eid}_{i}")
                st.session_state.etappe_keuzes[eid][i] = keuze if keuze != "-" else None

            # Reset knop voor deze etappe
            if any(st.session_state.etappe_keuzes[eid]):
                if st.button(f"↩️ Reset etappe {etappe['id']}", key=f"reset_{eid}"):
                    st.session_state.etappe_keuzes[eid] = [None, None, None]
                    st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 2: TEAM SAMENSTELLEN
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Stap 1 — Jouw Picks Overzicht")
    st.caption("Renners die jij vaker hebt gekozen krijgen een hogere prioriteit bij het samenstellen.")

    draft_data = []
    for eid, keuzes in st.session_state.etappe_keuzes.items():
        for i, r in enumerate(keuzes):
            if r and r != "-":
                draft_data.append({"Naam": r, "Punten": 3 - i})

    draft_counts = {}
    if draft_data:
        draft_df = pd.DataFrame(draft_data)
        draft_summary = (
            draft_df.groupby("Naam")["Punten"]
            .sum().reset_index()
            .sort_values(by="Punten", ascending=False)
        )
        draft_summary = pd.merge(draft_summary, df[['Naam', 'Prijs', 'EV']], on='Naam', how='left')
        draft_summary.columns = ['Renner', 'Jouw Score', 'Prijs (M)', 'EV']

        # Kleurcodering: hoe vaker gekozen, hoe groener
        max_score = draft_summary['Jouw Score'].max()
        def kleur(val):
            pct = val / max_score if max_score > 0 else 0
            g = int(100 + pct * 155)
            return f'background-color: rgba(0,{g},0,0.15)'

        st.dataframe(
            draft_summary.style.applymap(kleur, subset=['Jouw Score']),
            hide_index=True, use_container_width=True
        )
        draft_counts = dict(zip(draft_summary['Renner'], draft_summary['Jouw Score']))
    else:
        st.info("Je hebt nog geen etappes ingevuld in Tab 1. De assistent kan dan alleen op stats optimaliseren.")

    st.divider()
    st.subheader("Stap 2 — Stel je 16 samen")

    col_auto, col_manual = st.columns([1, 2])

    with col_auto:
        st.markdown("**🤖 Laat de assistent kiezen**")
        max_bud_inp = st.number_input("Budget (M€)", value=100.0, step=0.5)
        max_ren_inp = st.number_input("Aantal renners", value=16, min_value=1, max_value=25)

        if st.button("🚀 Bereken optimaal team", type="primary", use_container_width=True):
            res = solve_final_team(df, draft_counts, max_bud_inp, max_ren_inp)
            if res:
                st.session_state.finaal_team = res
                st.rerun()
            else:
                st.error("Kon geen geldig team berekenen binnen het budget.")

    with col_manual:
        st.markdown("**✏️ Of kies handmatig**")

        def update_finaal_team():
            st.session_state.finaal_team = st.session_state._finaal_team_selector

        st.multiselect(
            "Selecteer je 16 renners:",
            options=df['Naam'].tolist(),
            default=st.session_state.finaal_team,
            max_selections=16,
            key="_finaal_team_selector",
            on_change=update_finaal_team,
        )

    st.divider()
    if not huidig_team_df.empty:
        st.subheader("Stap 3 — Jouw definitieve selectie")
        col_grafiek, col_tabel = st.columns([1, 2])
        with col_grafiek:
            plot_cols = [c for c in ['GC', 'SPR', 'ITT', 'MTN'] if c in huidig_team_df.columns]
            if plot_cols:
                st.markdown("**Gemiddelde team stats:**")
                st.bar_chart(huidig_team_df[plot_cols].mean())
        with col_tabel:
            show_cols = [c for c in ['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV'] if c in huidig_team_df.columns]
            st.dataframe(
                huidig_team_df[show_cols].sort_values(by='Prijs', ascending=False),
                hide_index=True, use_container_width=True
            )

        # Budget check
        if totaal_prijs > 100:
            st.error(f"🚨 Budget overschreden met €{totaal_prijs - 100:.2f}M!")
        elif totaal_prijs > 98:
            st.success(f"✅ Budget optimaal benut: €{totaal_prijs:.2f}M / €100M")
        else:
            st.info(f"💰 Nog €{100 - totaal_prijs:.2f}M over.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 3: OPSTELLINGEN
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    if not st.session_state.finaal_team:
        st.warning("Stel eerst je team van 16 samen in Tab 2.")
    else:
        st.subheader("📅 Dagopstellingen & Kopman advies")
        st.caption(
            "Per etappe zie je je beste 9 en de geadviseerde kopman (de renner met de hoogste etappescore). "
            "Jouw eigen picks krijgen altijd voorrang."
        )

        # Matrix
        matrix_data = {renner: {"Renner": renner} for renner in st.session_state.finaal_team}
        for etappe in GIRO_ETAPPES:
            eid      = str(etappe["id"])
            col_name = f"E{etappe['id']}"
            cw       = st.session_state.giro_weights_v2[eid]
            emoji    = TYPE_EMOJI.get(etappe["type"], "")

            for renner in st.session_state.finaal_team:
                matrix_data[renner][col_name] = "-"

            voorspelde_namen = [n for n in st.session_state.etappe_keuzes[eid] if n and n in st.session_state.finaal_team]
            som_input = sum(cw.values())
            w = ({k: cw[k]/som_input for k in cw} if som_input > 0
                 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25})

            team_stage_df = huidig_team_df.copy()
            team_stage_df['StageScore'] = (
                team_stage_df['SPR'] * w['SPR'] + team_stage_df['GC'] * w['GC'] +
                team_stage_df['ITT'] * w['ITT'] + team_stage_df['MTN'] * w['MTN']
            )

            voorspeld_df = (team_stage_df.set_index('Naam').loc[voorspelde_namen].reset_index()
                            if voorspelde_namen and 'Naam' in team_stage_df.columns else pd.DataFrame())
            rest_df = team_stage_df[~team_stage_df['Naam'].isin(voorspelde_namen)].sort_values(
                by=['StageScore', 'EV'], ascending=[False, False])
            top_9_df = pd.concat([voorspeld_df, rest_df]).head(9)

            for i, (_, row) in enumerate(top_9_df.iterrows()):
                matrix_data[row['Naam']][col_name] = f"{emoji}©" if i == 0 else f"{emoji}✅"

        matrix_df = pd.DataFrame(list(matrix_data.values()))
        st.dataframe(matrix_df, hide_index=True, use_container_width=True)

        st.divider()
        st.subheader("🔍 Etappe Details")

        for etappe in GIRO_ETAPPES:
            eid   = str(etappe["id"])
            cw    = st.session_state.giro_weights_v2[eid]
            emoji = TYPE_EMOJI.get(etappe["type"], "")

            voorspelde_namen = [n for n in st.session_state.etappe_keuzes[eid] if n and n in st.session_state.finaal_team]
            som_input = sum(cw.values())
            w = ({k: cw[k]/som_input for k in cw} if som_input > 0
                 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25})

            team_stage_df = huidig_team_df.copy()
            team_stage_df['StageScore'] = (
                team_stage_df['SPR'] * w['SPR'] + team_stage_df['GC'] * w['GC'] +
                team_stage_df['ITT'] * w['ITT'] + team_stage_df['MTN'] * w['MTN']
            )

            voorspeld_df = (team_stage_df.set_index('Naam').loc[voorspelde_namen].reset_index()
                            if voorspelde_namen and 'Naam' in team_stage_df.columns else pd.DataFrame())
            rest_df = team_stage_df[~team_stage_df['Naam'].isin(voorspelde_namen)].sort_values(
                by=['StageScore', 'EV'], ascending=[False, False])
            top_9_df = pd.concat([voorspeld_df, rest_df]).head(9)

            with st.expander(f"E{etappe['id']} {emoji} {etappe['route']} ({etappe['date']})"):
                opstelling = []
                for i, (_, row) in enumerate(top_9_df.iterrows()):
                    naam = row['Naam']
                    if i == 0:
                        rol = "© Kopman (geadviseerd)"
                    elif naam in voorspelde_namen:
                        rol = "Basis (jouw pick)"
                    else:
                        rol = "Basis (assistent aanvulling)"
                    opstelling.append({"Rol": rol, "Renner": naam, "Score": int(row['StageScore'])})

                st.dataframe(pd.DataFrame(opstelling), hide_index=True, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 4: STARTLIJST
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Volledige Startlijst & Statistieken")
    search = st.text_input("🔍 Zoek op naam of ploeg:")
    show_cols = [c for c in ['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV'] if c in df.columns]
    display_df = df[show_cols].copy()
    if search:
        mask = display_df['Naam'].str.contains(search, case=False, na=False)
        if 'Ploeg' in display_df.columns:
            mask |= display_df['Ploeg'].str.contains(search, case=False, na=False)
        display_df = display_df[mask]
    st.dataframe(display_df.sort_values(by='Prijs', ascending=False), hide_index=True, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 5: UITLEG
# ════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("ℹ️ Hoe werkt de Team Bouwer?")

    st.warning("""
    **⚠️ LET OP: Voorlopige Data!**
    De startlijst en prijzen zijn een inschatting. Ze worden bijgewerkt zodra de officiële Sporza Giro-lancering plaatsvindt.
    """)

    st.markdown("""
    De **Team Bouwer** is de tegenhanger van de AI Solver. Hier bouw jij je team — de assistent helpt je
    onderweg met suggesties, maar jij hebt het laatste woord.

    ---

    ### 🗺️ Tab 1 — Etappe Picks
    Loop etappe voor etappe door het parcours:
    - Bekijk de kaart en het hoogteprofiel.
    - Pas de profielwegingen aan als jij denkt dat het type anders uitpakt (bijv. meer MTN dan de standaard voorspelt).
    - De assistent toont de top 5 renners op basis van jouw weging.
    - Klik **Neem top 3 over** om direct in te vullen, of kies zelf via de dropdowns.

    ### 🛡️ Tab 2 — Team Samenstellen
    Jouw picks worden samengevat in een scoretabel: renners die je vaker hebt gekozen staan hoger.
    - **Automatisch**: de solver bouwt het beste 16-koppige team dat binnen €100M past, met jouw favorieten als prioriteit.
    - **Handmatig**: selecteer zelf de 16 renners via de multiselect.

    ### 🚀 Tab 3 — Opstellingen
    Per etappe zie je de ideale 9 uit jouw 16, inclusief de geadviseerde kopman.
    - Jouw eigen picks (Tab 1) krijgen altijd voorrang als basisplaats.
    - De eerste renner op basis van de etappescore wordt kopman.
    - De matrix bovenaan geeft een overzicht van alle 21 etappes in één oogopslag.

    ---

    ### 🤖 Verschil met de AI Solver
    | | AI Solver | Team Bouwer |
    |---|---|---|
    | **Etappe analyse** | Claude AI (volledig automatisch) | Jij kiest, assistent adviseert |
    | **Team selectie** | Wiskundige optimalisatie | Jij bepaalt, solver vult aan |
    | **Kopman** | Puur op stats | Jouw picks krijgen voorrang |
    | **Ideaal voor** | Snel een sterk AI-team | Eigen wielerkennis inbrengen |
    """)
