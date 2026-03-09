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

# --- ETAPPE DATA (Inclusief wegingen) ---
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

def get_team_from_etappes():
    gekozen = set()
    for etappe_id in st.session_state.etappe_keuzes:
        for renner in st.session_state.etappe_keuzes[etappe_id]:
            if renner: gekozen.add(renner)
    return list(gekozen)

huidig_team_namen = get_team_from_etappes()
huidig_team_df = df[df['Naam'].isin(huidig_team_namen)]
totaal_prijs = huidig_team_df['Prijs'].sum() if not huidig_team_df.empty else 0
aantal_renners = len(huidig_team_namen)

# --- SIDEBAR ---
with st.sidebar:
    st.title("📋 Team Status")
    st.metric("Budget over", f"€ {100 - totaal_prijs:.2f}M")
    st.metric("Renners", f"{aantal_renners} / 16")
    
    if aantal_renners > 16: st.error("🚨 Te veel unieke renners!")
    if totaal_prijs > 100: st.error("🚨 Budget overschreden!")

    st.divider()
    if st.button("💾 Opslaan", type="primary", use_container_width=True):
        data = {
            "team": huidig_team_namen, 
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
            st.rerun()

# --- HOOFDSCHERM ---
st.title("🇮🇹 Handmatige Team Bouwer")
st.markdown("*Data en Statistieken van [Wielerorakel](https://wielerorakel.nl/)*")

if df.empty:
    st.error("Databestanden niet gevonden. Controleer de mappen.")
    st.stop()

renners_opties = ["-"] + sorted(df['Naam'].tolist())

# --- TABS AANMAKEN ---
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Etappe Voorspellingen", "🛡️ Jouw Team", "📋 Startlijst", "ℹ️ Uitleg"])

# TAB 1: ETAPPE VOORSPELLINGEN
with tab1:
    st.info("Kies per etappe de renners waarvan jij denkt dat ze gaan scoren. Speel met de weging om de AI-suggesties te beïnvloeden. De app bouwt je team van 16 man automatisch op in de achtergrond.")
    
    # Waarschuwing als je al op 16 zit
    if aantal_renners >= 16:
        st.warning("⚠️ Je hebt 16 of meer unieke renners geselecteerd. Wil je iemand toevoegen, verwijder dan eerst iemand in een andere etappe.")

    for etappe in GIRO_ETAPPES:
        eid = str(etappe["id"])
        
        with st.expander(f"Etappe {etappe['id']}: {etappe['route']} ({etappe['type']})"):
            giro_link = "https://www.giroditalia.it/en/the-route/"
            map_path = f"giro262/giro26-{etappe['id']}-map.jpg"
            prof_path = f"giro262/giro26-{etappe['id']}-hp.jpg" 
            
            i1, i2 = st.columns(2)
            i1.markdown(get_clickable_image_html(map_path, f"Kaart+Etappe+{etappe['id']}", giro_link), unsafe_allow_html=True)
            i2.markdown(get_clickable_image_html(prof_path, f"Profiel+Etappe+{etappe['id']}", giro_link), unsafe_allow_html=True)
            
            st.divider()
            
            # Aanpassen weging
            st.markdown("###### ⚙️ Pas de weging aan voor andere suggesties:")
            cw = st.session_state.giro_weights_v2[eid]
            wc1, wc2, wc3, wc4 = st.columns(4)
            new_spr = wc1.number_input("Sprint (SPR)", 0.0, 1.0, float(cw["SPR"]), 0.1, key=f"wspr_{eid}")
            new_gc  = wc2.number_input("Klassement (GC)", 0.0, 1.0, float(cw["GC"]), 0.1, key=f"wgc_{eid}")
            new_itt = wc3.number_input("Tijdrit (ITT)", 0.0, 1.0, float(cw["ITT"]), 0.1, key=f"witt_{eid}")
            new_mtn = wc4.number_input("Klim/Aanval (MTN)", 0.0, 1.0, float(cw["MTN"]), 0.1, key=f"wmtn_{eid}")
            
            # Sla direct de nieuwe weging op
            st.session_state.giro_weights_v2[eid] = {"SPR": new_spr, "GC": new_gc, "ITT": new_itt, "MTN": new_mtn}
            active_weights = st.session_state.giro_weights_v2[eid]
            
            # Bereken top 5 suggesties op basis van (nieuwe) weging
            df_stage = df.copy()
            df_stage['StageScore'] = (df_stage['SPR'] * active_weights['SPR'] + 
                                      df_stage['GC'] * active_weights['GC'] + 
                                      df_stage['ITT'] * active_weights['ITT'] + 
                                      df_stage['MTN'] * active_weights['MTN'])
            top_5 = df_stage.sort_values(by=['StageScore', 'EV'], ascending=[False, False]).head(5)
            top_5_namen = [f"{row['Naam']} ({int(row['StageScore'])})" for _, row in top_5.iterrows()]
            
            st.info(f"💡 **AI Top 5 Suggesties:** {', '.join(top_5_namen)}")
            
            # Voorspelling selecties
            st.markdown("###### Jouw Voorspelling:")
            c1, c2, c3 = st.columns(3)
            for i, col in enumerate([c1, c2, c3]):
                current_val = st.session_state.etappe_keuzes[eid][i]
                d_idx = renners_opties.index(current_val) if current_val in renners_opties else 0
                
                keuze = col.selectbox(f"Positie {i+1}", renners_opties, index=d_idx, key=f"sel_{eid}_{i}")
                st.session_state.etappe_keuzes[eid][i] = keuze if keuze != "-" else None

# TAB 2: JOUW TEAM
with tab2:
    st.subheader("Analyse van jouw gekozen team")
    if huidig_team_df.empty:
        st.info("Je hebt nog geen renners gekozen. Ga naar het tabblad 'Etappe Voorspellingen' om te beginnen.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Aantal Renners", f"{aantal_renners} / 16")
        c2.metric("Budget Besteed", f"€ {totaal_prijs:.2f}M")
        c3.metric("Budget Over", f"€ {100 - totaal_prijs:.2f}M")

        st.divider()
        col_grafiek, col_tabel = st.columns([1, 2])
        
        with col_grafiek:
            st.write("**Gemiddelde Team Stats:**")
            plot_cols = [c for c in ['GC', 'SPR', 'ITT', 'MTN'] if c in huidig_team_df.columns]
            if plot_cols:
                st.bar_chart(huidig_team_df[plot_cols].mean())

        with col_tabel:
            st.write("**Huidige Selectie:**")
            st.dataframe(
                huidig_team_df[['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV']].sort_values(by='Prijs', ascending=False), 
                hide_index=True, 
                use_container_width=True
            )

        # Laat zien in hoeveel etappes elke renner is gekozen
        st.subheader("Inzetbaarheid")
        renner_etappes = {renner: [] for renner in huidig_team_namen}
        for eid, keuzes in st.session_state.etappe_keuzes.items():
            for renner in keuzes:
                if renner:
                    renner_etappes[renner].append(eid)
                    
        for renner, ritten in renner_etappes.items():
            if ritten:
                st.write(f"**{renner}** is ingezet in rit(ten): {', '.join(ritten)}")

# TAB 3: STARTLIJST
with tab3:
    st.subheader("Volledige Startlijst & Prijzen")
    st.write("Blader door alle beschikbare renners. Tip: Klik op een kolomkop om te sorteren.")
    st.dataframe(
        df[['Naam', 'Ploeg', 'Prijs', 'GC', 'SPR', 'ITT', 'MTN', 'EV']].sort_values(by='Prijs', ascending=False),
        hide_index=True,
        use_container_width=True
    )

# TAB 4: UITLEG
with tab4:
    st.header("ℹ️ Uitleg & Disclaimer")
    
    st.warning("""
    **⚠️ LET OP: Voorlopige Data!**
    De huidige startlijst en de daaraan gekoppelde prijzen zijn op dit moment nog **niet compleet en deels een inschatting**. 
    Zodra de echte Giro d'Italia dichterbij komt en de definitieve prijzen gelanceerd zijn, worden deze bestanden geüpdatet!
    """)
    
    st.markdown("""
    ### 🛠️ Hoe werkt de 'Handmatige Bouwer'?
    In tegenstelling tot de AI-Solver, heb je hier zelf de volledige controle over de 16 renners in je team. 

    **1. Bouwen vanuit het parcours**
    Je stelt je team niet samen vanuit een droge lijst, maar **per etappe**. 
    - Klap een etappe uit in het tabblad *Etappe Voorspellingen*.
    - Bekijk het hoogteprofiel en de route.
    - Speel met de wegingen (bijvoorbeeld meer SPR of meer MTN) om de AI-Suggesties te beïnvloeden.
    - Kies de 3 renners waarvan jij denkt dat ze daar de meeste punten pakken.

    **2. Automatische Teamlijst**
    Zodra je een renner kiest in een etappe, wordt deze **automatisch aan je team toegevoegd** (zichtbaar in het tabblad *Jouw Team* en de zijbalk).
    Kies je dezelfde renner in meerdere etappes? Geen probleem, hij neemt uiteraard maar 1 van de 16 plekjes in.

    **3. Budget & Limieten**
    Net als in het echte spel ben je gebonden aan regels:
    - Maximaal **16 renners** in totaal.
    - Maximaal **€ 100 Miljoen** budget.
    De balk aan de zijkant kleurt rood als je over je limiet heen gaat. Om weer binnen de limiet te vallen, moet je renners verwijderen (vervang ze door een streepje `-` in de etappes waar je ze had geselecteerd).
    
    **Wat betekenen de categorieën?**
    - **SPR (Sprint):** Typische vlakke aankomsten voor de rappe mannen.
    - **GC (Klassement):** Zware bergritten waar de klassementsmannen het uitvechten.
    - **ITT (Tijdrit):** Voordeel voor de pure tijdrijders.
    - **MTN (Aanval/Klim):** Ritten voor vluchters, punchers en de vroege ontsnapping.
    """)
