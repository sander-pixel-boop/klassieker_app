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

# --- CSS HACK: VERBERG ZIJBALK VOOR INLOGGEN ---
def hide_sidebar():
    st.markdown("""
        <style>
            [data-testid="collapsedControl"] {display: none;}
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

# --- INLOG PAGINA (Landingspagina Lay-out) ---
def login_page():
    hide_sidebar()
    
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
