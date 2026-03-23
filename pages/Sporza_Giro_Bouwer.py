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
    {"id": 1, "date": "08/05", "route": "Nessebar - Burgas", "type": "Vlak", "w": {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0}},
    {"id": 2, "date": "09/05", "route": "Burgas - Valiko Tarnovo", "type": "Heuvel", "w": {"SPR": 0.3, "GC": 0.3, "ITT": 0.0, "MTN": 0.4}},
    {"id": 3, "date": "10/05", "route": "Plovdiv - Sofia", "type": "Vlak/Heuvel", "w": {"SPR": 0.9, "GC": 0.0, "ITT": 0.0, "MTN": 0.1}},
    {"id": 4, "date": "12/05", "route": "Catanzaro - Cosenza", "type": "Vlak/Heuvel", "w": {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4}},
    {"id": 5, "date": "13/05", "route": "Praia a Mare - Potenza", "type": "Heuvel", "w": {"SPR": 0.1, "GC": 0.6, "ITT": 0.0, "MTN": 0.3}},
    {"id": 6, "date": "14/05", "route": "Paestum - Naples", "type": "Heuvel", "w": {"SPR": 0.8, "GC": 0.0, "ITT": 0.0, "MTN": 0.2}},
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
                            if 'GC' in df_scores.columns: e['w']['GC'] = float(row['GC'])
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
    if not os.path.exists(prijzen_file) or not os.path.exists(stats_file): return pd.DataFrame()
    
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
        
    df['EV'] = ((df['GC']/100)**4 * 400 + (df['SPR']/100)**4 * 250 + (df['ITT']/100)**4 * 80 + (df['MTN']/100)**4 * 100).fillna(0).round(0)
    
    if naam_col_p != 'Naam': df = df.rename(columns={naam_col_p: 'Naam'})
    return df.sort_values('Naam')

df = load_all_data()

# --- SESSION STATE INITIALISATIE ---
if "etappe_keuzes" not in st.session_state:
    st.session_state.etappe_keuzes = {str(e["id"]): [None, None, None] for e in GIRO_ETAPPES}
if "giro_weights_v2" not in st.session_state:
    st.session_state.giro_weights_v2 = {str(e["id"]): e["w"].copy() for e in GIRO_ETAPPES}
if "finaal_team" not in st.session_state:
    st.session_state.finaal_team = []

huidig_team_namen = st.session_state.finaal_team
huidig_team_df = df[df['Naam'].isin(huidig_team_namen)].copy()
totaal_prijs = huidig_team_df['Prijs'].sum() if not huidig_team_df.empty else 0
aantal_renners = len(huidig_team_namen)

# --- SIDEBAR ---
with st.sidebar:
    st.title("📋 Definitieve Team Status")
    st.metric("Budget over", f"€ {100 - totaal_prijs:.2f}M")
    st.metric("Renners", f"{aantal_renners} / 16")
    
    if aantal_renners > 16: st.error("🚨 Te veel unieke renners!")
    if totaal_prijs > 100: st.error("🚨 Budget overschreden!")

    st.divider()
    if st.button("💾 Opslaan", type="primary", use_container_width=True):
        data = {
            "team": st.session_state.finaal_team, 
            "etappe_keuzes": st.session_state.etappe_keuzes,
            "weights": st.session_state.giro_weights_v2
        }
        supabase.table(TABEL_NAAM).update({DB_KOLOM: data}).eq("username", speler_naam).execute()
        st.success("Opgeslagen!")
        
    if st.button("🔄 Inladen", use_container_width=True):
        res = supabase.table(TABEL_NAAM).select(DB_KOLOM).eq("username", speler_naam).execute()
        if res.data and res.data[0].get(DB_KOLOM):
            db_data = res.data[0][DB_KOLOM]
            st.session_state.etappe_keuzes = db_data.get("etappe_keuzes", {str(e["id"]): [None]*3 for e in GIRO_ETAPPES})
            st.session_state.giro_weights_v2 = db_data.get("weights", {str(e["id"]): e["w"].copy() for e in GIRO_ETAPPES})
            st.session_state.finaal_team = db_data.get("team", [])
            st.rerun()

# --- HOOFDSCHERM ---
st.title("🇮🇹 Handmatige Team Bouwer")
st.markdown("*Data en Statistieken van [Wielerorakel](https://wielerorakel.nl/)*")

if df.empty:
    st.error("Databestanden niet gevonden. Controleer de mappen.")
    st.stop()

# --- TABS AANMAKEN ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Etappe Voorspellingen", "🛡️ Finaal Team Samenstellen", "🚀 Opstellingen", "📋 Startlijst", "ℹ️ Uitleg"])

# TAB 1: ETAPPE VOORSPELLINGEN
with tab1:
    st.info("Kies onbeperkt per etappe de renners waarvan jij denkt dat ze gaan scoren. In Tab 2 stellen we op basis hiervan het definitieve team samen.")
    
    sorteer_optie = st.radio("Sorteer dropdown-lijsten op:", ["🔤 Alfabetisch", "📊 Verwachte Waarde (Algemene EV)"], horizontal=True)
    
    if "Alfabetisch" in sorteer_optie:
        renners_opties = ["-"] + sorted(df['Naam'].tolist())
    else:
        renners_opties = ["-"] + df.sort_values(by='EV', ascending=False)['Naam'].tolist()

    for etappe in GIRO_ETAPPES:
        eid = str(etappe["id"])
        cw = st.session_state.giro_weights_v2[eid]
        
        som_header = sum(cw.values()) if sum(cw.values()) > 0 else 1.0
        weight_str = f"SPR:{int((cw['SPR']/som_header)*100)}% GC:{int((cw['GC']/som_header)*100)}% ITT:{int((cw['ITT']/som_header)*100)}% MTN:{int((cw['MTN']/som_header)*100)}%"
        
        with st.expander(f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']}) | 🤖 {weight_str}"):
            giro_link = "https://www.giroditalia.it/en/the-route/"
            map_path = f"giro262/giro26-{etappe['id']}-map.jpg"
            prof_path = f"giro262/giro26-{etappe['id']}-hp.jpg" 
            
            i1, i2 = st.columns(2)
            i1.markdown(get_clickable_image_html(map_path, f"Kaart+Etappe+{etappe['id']}", giro_link), unsafe_allow_html=True)
            i2.markdown(get_clickable_image_html(prof_path, f"Profiel+Etappe+{etappe['id']}", giro_link), unsafe_allow_html=True)
            
            st.divider()
            
            st.markdown("###### ⚙️ Pas de weging aan voor andere suggesties:")
            wc1, wc2, wc3, wc4 = st.columns(4)
            new_spr = wc1.number_input("Sprint (SPR)", 0.0, 1.0, float(cw["SPR"]), 0.1, key=f"wspr_{eid}")
            new_gc  = wc2.number_input("Klassement (GC)", 0.0, 1.0, float(cw["GC"]), 0.1, key=f"wgc_{eid}")
            new_itt = wc3.number_input("Tijdrit (ITT)", 0.0, 1.0, float(cw["ITT"]), 0.1, key=f"witt_{eid}")
            new_mtn = wc4.number_input("Klim/Aanval (MTN)", 0.0, 1.0, float(cw["MTN"]), 0.1, key=f"wmtn_{eid}")
            
            st.session_state.giro_weights_v2[eid] = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}
            
            som_input = new_spr + new_gc + new_itt + new_mtn
            if abs(som_input - 1.0) > 0.01 and som_input > 0:
                st.warning(f"⚠️ Jouw weging telt op tot **{som_input*100:.0f}%**. Dit wordt op de achtergrond teruggeschaald naar exact 100%.")
                active_weights = {"SPR": new_spr/som_input, "GC": new_gc/som_input, "ITT": new_itt/som_input, "MTN": new_mtn/som_input}
            elif som_input == 0:
                st.error("⚠️ Weging mag niet 0% zijn. Er wordt tijdelijk een standaardverdeling gebruikt.")
                active_weights = {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
            else:
                active_weights = st.session_state.giro_weights_v2[eid]
            
            df_stage = df.copy()
            df_stage['StageScore'] = (df_stage['SPR'] * active_weights['SPR'] + 
                                      df_stage['GC'] * active_weights['GC'] + 
                                      df_stage['ITT'] * active_weights['ITT'] + 
                                      df_stage['MTN'] * active_weights['MTN'])
            top_5 = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False]).head(5)
            top_5_namen = [f"{row['Naam']} ({int(row['StageScore'])})" for _, row in top_5.iterrows()]
            top_3_pure_names = top_5['Naam'].tolist()[:3]
            
            st.info(f"💡 **AI Top 5 Suggesties:** {', '.join(top_5_namen)}")
            
            c_pred_head, c_pred_btn = st.columns([3, 1])
            with c_pred_head:
                st.markdown("###### Jouw Voorspelling:")
            with c_pred_btn:
                if st.button("🤖 Neem AI Top 3 over", key=f"btn_ai_{eid}"):
                    for idx, naam in enumerate(top_3_pure_names):
                        st.session_state.etappe_keuzes[eid][idx] = naam
                    st.rerun()

            c1, c2, c3 = st.columns(3)
            for i, col in enumerate([c1, c2, c3]):
                current_val = st.session_state.etappe_keuzes[eid][i]
                d_idx = renners_opties.index(current_val) if current_val in renners_opties else 0
                
                keuze = col.selectbox(f"Positie {i+1}", renners_opties, index=d_idx, key=f"sel_{eid}_{i}")
                st.session_state.etappe_keuzes[eid][i] = keuze if keuze != "-" else None

# TAB 2: FINAAL TEAM SAMENSTELLEN
with tab2:
    st.subheader("1. Jouw Voorspellingen Overzicht")
    st.write("Hier zie je een verzameling van alle renners die je in Tab 1 hebt geselecteerd. Ze krijgen punten per voorspelling (Pos 1 = 3pt, Pos 2 = 2pt, Pos 3 = 1pt).")
    
    draft_data = []
    for eid, keuzes in st.session_state.etappe_keuzes.items():
        for i, r in enumerate(keuzes):
            if r and r != "-":
                draft_data.append({"Naam": r, "Punten": 3-i})
    
    draft_df = pd.DataFrame(draft_data)
    draft_counts = {}
    if not draft_df.empty:
        draft_summary = draft_df.groupby("Naam")["Punten"].sum().reset_index().sort_values(by="Punten", ascending=False)
        draft_summary = pd.merge(draft_summary, df[['Naam', 'Prijs', 'EV']], on='Naam', how='left')
        st.dataframe(draft_summary, hide_index=True, use_container_width=True)
        draft_counts = dict(zip(draft_summary['Naam'], draft_summary['Punten']))
    else:
        st.info("Je hebt nog geen etappes voorspeld in Tab 1.")

    st.divider()
    st.subheader("2. Finaal Team Selecteren (16 Renners)")
    
    c_auto, c_space = st.columns([1, 2])
    with c_auto:
        if st.button("🤖 Bereken Optimaal Team obv Voorspellingen", type="primary", use_container_width=True):
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
    c2.metric("Budget Besteed", f"€ {totaal_prijs:.2f}M")
    c3.metric("Budget Over", f"€ {100 - totaal_prijs:.2f}M")

# TAB 3: OPSTELLINGEN
with tab3:
    st.subheader("🚀 Optimale Opstelling per Etappe")
    if not st.session_state.finaal_team:
        st.warning("Stel eerst je definitieve team van 16 samen in Tab 2.")
    else:
        st.write("Hier zie je per etappe de ideale basisopstelling en Kopman gehaald uit je definitieve team. Jouw eigen voorspellingen krijgen altijd voorrang.")
        for etappe in GIRO_ETAPPES:
            eid = str(etappe["id"])
            cw = st.session_state.giro_weights_v2[eid]
            
            voorspelde_namen = [naam for naam in st.session_state.etappe_keuzes[eid] if naam and naam in st.session_state.finaal_team]
            
            som_input = sum(cw.values())
            w = {"SPR": cw['SPR']/som_input, "GC": cw['GC']/som_input, "ITT": cw['ITT']/som_input, "MTN": cw['MTN']/som_input} if som_input > 0 else {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25}
            
            team_stage_df = huidig_team_df.copy()
            team_stage_df['StageScore'] = (team_stage_df['SPR'] * w['SPR'] + team_stage_df['GC'] * w['GC'] + team_stage_df['ITT'] * w['ITT'] + team_stage_df['MTN'] * w['MTN'])
            
            if voorspelde_namen:
                voorspeld_df = team_stage_df.set_index('Naam').loc[voorspelde_namen].reset_index()
            else:
                voorspeld_df = pd.DataFrame()
                
            rest_df = team_stage_df[~team_stage_df['Naam'].isin(voorspelde_namen)].sort_values(by=['StageScore', 'EV'], ascending=[False, False])
            
            top_9_df = pd.concat([voorspeld_df, rest_df]).head(9)
            
            with st.expander(f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']})"):
                opstelling = []
                for i, (_, row) in enumerate(top_9_df.iterrows()):
                    if i == 0:
                        rol = "© Kopman"
                    elif row['Naam'] in voorspelde_namen:
                        rol = "Basis (Jouw Voorspelling)"
                    else:
                        rol = "Basis (AI Opvulling)"
                        
                    opstelling.append({"Rol": rol, "Renner": row['Naam'], "Verwachte Score": int(row['StageScore'])})
                st.dataframe(pd.DataFrame(opstelling), hide_index=True, use_container_width=True)

# TAB 4: STARTLIJST
with tab4:
    st.subheader("Volledige Startlijst & Prijzen")
    st.dataframe(
        df[['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV']].sort_values(by='Prijs', ascending=False),
        hide_index=True,
        use_container_width=True
    )

# TAB 5: UITLEG
with tab5:
    st.header("ℹ️ Uitleg & Disclaimer")
    
    st.warning("""
    **⚠️ LET OP: Voorlopige Data!**
    De huidige startlijst en de daaraan gekoppelde prijzen zijn op dit moment nog **niet compleet en deels een inschatting**. 
    Zodra de echte Giro d'Italia dichterbij komt en de definitieve prijzen gelanceerd zijn, worden deze bestanden geüpdatet!
    """)
    
    st.markdown("""
    ### 🛠️ Hoe werkt de 'Handmatige Bouwer'?
    
    **1. Bouwen vanuit het parcours (Tab 1)**
    Kies onbeperkt renners per etappe. Bekijk het hoogteprofiel en de route. Speel met de wegingen om de AI-Suggesties te beïnvloeden en neem de AI Top 3 met één druk op de knop over.

    **2. Definitief team bepalen (Tab 2)**
    In dit tabblad zie je welke renners je het vaakst voorspeld hebt. Selecteer je definitieve 16 renners handmatig via de dropdown, of druk op de Auto-Solve knop om de AI de 16 beste renners binnen het budget van €100M te laten kiezen.
    
    **3. Dagopstellingen (Tab 3)**
    Hier zie je direct de ideale 9-koppige opstelling voor elke dag gehaald uit jouw gekozen 16. Jouw eigen voorspellingen (uit Tab 1) krijgen altijd voorrang als basisplaats en de nummer 1 voorspelling wordt automatisch Kopman. De rest wordt logisch aangevuld.
    """)
