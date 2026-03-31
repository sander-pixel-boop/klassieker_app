import streamlit as st
import hashlib
from supabase import create_client

st.set_page_config(page_title="Wieler Spellen Solver", page_icon="🚴‍♂️", layout="wide")

# --- DATABASE CONNECTIE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()
TABEL_NAAM = "gebruikers_data_test"

def hash_wachtwoord(wachtwoord):
    return hashlib.sha256(wachtwoord.encode()).hexdigest()

# --- INLOG PAGINA (Landingspagina Lay-out) ---
def login_page():
    st.markdown("<h1 style='text-align: center; margin-bottom: 50px;'>🚴‍♂️ Wieler Spellen Solver</h1>", unsafe_allow_html=True)
    
    col_links, col_spacer, col_rechts = st.columns([1.2, 0.2, 1])
    
    with col_links:
        st.header("Welkom!")
        st.markdown("De ultieme AI-tool voor je wielermanagerspellen. Combineer data met wiskundige optimalisatie en bereken de perfecte selectie.")
        
        st.divider()
        st.markdown("### 🏆 Ondersteunde Spellen")
        st.markdown("- **Scorito** (Klassiekers & Grand Tours)")
        st.markdown("- **Sporza** (Klassiekers & Grand Tours)")
        st.markdown("- **Cycling Fantasy**")
        
        st.divider()
        st.markdown("### 🧠 Features")
        st.markdown("✅ Wiskundige AI Solvers (Knapsack optimalisatie)\n✅ Verwachte Waarde (EV) berekeningen op basis van parcours\n✅ Dynamische wissel- en transferstrategieën\n✅ Live Model Evaluator")
        st.markdown("*Data: [Wielerorakel.nl](https://wielerorakel.nl/)*")

    with col_rechts:
        with st.container(border=True):
            st.subheader("🔒 Log in of Registreer")
            tab1, tab2 = st.tabs(["Inloggen", "Account Aanmaken"])
            
            with tab1:
                inlog_naam = st.text_input("Gebruikersnaam", key="inlog_naam")
                inlog_ww = st.text_input("Wachtwoord", type="password", key="inlog_ww")
                if st.button("Inloggen", type="primary", use_container_width=True):
                    if inlog_naam and inlog_ww:
                        res = supabase.table(TABEL_NAAM).select("password").eq("username", inlog_naam.lower()).execute()
                        if res.data and res.data[0].get("password") == hash_wachtwoord(inlog_ww):
                            st.session_state["ingelogde_speler"] = inlog_naam.lower()
                            st.rerun()
                        else:
                            st.error("❌ Onjuiste gebruikersnaam of wachtwoord.")
                    else:
                        st.warning("Vul beide velden in.")
                        
            with tab2:
                nieuw_naam = st.text_input("Kies een Gebruikersnaam", key="nieuw_naam")
                nieuw_ww = st.text_input("Kies een Wachtwoord", type="password", key="nieuw_ww")
                if st.button("Maak account aan", use_container_width=True):
                    if nieuw_naam and nieuw_ww:
                        bestaat_al = supabase.table(TABEL_NAAM).select("username").eq("username", nieuw_naam.lower()).execute()
                        if bestaat_al.data:
                            st.error("❌ Deze gebruikersnaam is al in gebruik. Kies een andere.")
                        else:
                            try:
                                supabase.table(TABEL_NAAM).insert({
                                    "username": nieuw_naam.lower(),
                                    "password": hash_wachtwoord(nieuw_ww)
                                }).execute()
                                st.success("✅ Account succesvol aangemaakt! Je kunt nu inloggen.")
                            except Exception as e:
                                st.error(f"Fout bij aanmaken account: {e}")
                    else:
                        st.warning("Vul beide velden in.")
        
        st.write("")
        if st.button("🚪 Doorgaan als gast (zonder cloud-opslag)", use_container_width=True):
            st.session_state["ingelogde_speler"] = "gast"
            st.rerun()


# --- HOME PAGINA (INGELOGD) ---
def home_page():
    speler = st.session_state.get("ingelogde_speler", "bezoeker").capitalize()
    st.write(f"# Welkom bij het Dashboard, {speler}! 🚴‍♂️")
    st.markdown("*Kies een spel in het menu aan de linkerkant om je selectie te bouwen.*")
    st.divider()
    
    if st.button("Uitloggen", type="secondary"):
        del st.session_state["ingelogde_speler"]
        st.rerun()


# --- NAVIGATIE INSTELLEN ---
login = st.Page(login_page, title="Inloggen", icon="🔒")
home = st.Page(home_page, title="Home", icon="🏠", default=True)
cf_pagina = st.Page("pages/Cycling_Fantasy.py", title="CF Dashboard", icon="🚴")

# Scorito pagina's
scorito_klassiekers = st.Page("pages/Klassiekers - Scorito.py", title="Klassiekers", icon="🏆")
scorito_evaluator = st.Page("pages/Model_Evaluator_(Scorito).py", title="Evaluator", icon="📊")
scorito_giro = st.Page("pages/Scorito_Grand_Tour.py", title="[Binnenkort] Giro d'Italia", icon="🇮🇹")

# Sporza pagina's
sporza_klassiekers = st.Page("pages/Klassiekers - Sporza.py", title="Klassiekers", icon="🏁")
sporza_evaluator = st.Page("pages/Sporza_Evaluator.py", title="Evaluator", icon="📊")

# Sporza Grand Tour opties
sporza_giro_ai = st.Page("pages/Sporza_Giro.py", title="Giro: AI Solver", icon="🤖")
sporza_giro_bouwer = st.Page("pages/Sporza_Giro_Bouwer.py", title="Giro: Team Bouwer", icon="🛠️")
sporza_giro_evaluator = st.Page("pages/Sporza_Giro_Evaluator.py", title="[Beta] Giro: Evaluator", icon="📊")

# --- KEUZE: WEL OF NIET INGELOGD ---
if "ingelogde_speler" not in st.session_state:
    pg = st.navigation([login], position="hidden")
else:
    pg = st.navigation({
        "Info": [home],
        "Cycling Fantasy": [cf_pagina],
        "Scorito - Klassiekers": [scorito_klassiekers, scorito_evaluator],
        "Scorito - Grand Tours": [scorito_giro],
        "Sporza - Klassiekers": [sporza_klassiekers, sporza_evaluator],
        "Sporza - Grand Tours": [sporza_giro_ai, sporza_giro_bouwer, sporza_giro_evaluator]
    })

pg.run()
