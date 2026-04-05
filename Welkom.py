import streamlit as st
import hashlib
from utils.db import init_connection

st.set_page_config(page_title="Wieler Spellen Solver", page_icon="🚴‍♂️", layout="wide")

# --- DATABASE CONNECTIE ---
supabase = init_connection()
TABEL_NAAM = "gebruikers_data_test"

def hash_wachtwoord(wachtwoord):
    """
    Hashes a given password using SHA-256.

    Args:
        wachtwoord (str): The plain-text password to hash.

    Returns:
        str: The hashed password.
    """
    return hashlib.sha256(wachtwoord.encode()).hexdigest()

def check_login(username, password):
    """
    Checks if the given username and password match a record in the database.

    Args:
        username (str): The entered username.
        password (str): The entered plain-text password.

    Returns:
        bool: True if login is successful, False otherwise.
    """
    try:
        res = supabase.table(TABEL_NAAM).select("password").eq("username", username.lower()).execute()
        if res.data and res.data[0].get("password") == hash_wachtwoord(password):
            return True
        return False
    except Exception as e:
        return False

def create_account(username, password):
    """
    Creates a new user account in the database.

    Args:
        username (str): The desired username.
        password (str): The desired plain-text password.

    Returns:
        tuple[bool, str]: A tuple containing a boolean success flag and a message.
    """
    try:
        bestaat_al = supabase.table(TABEL_NAAM).select("username").eq("username", username.lower()).execute()
        if bestaat_al.data:
            return False, "❌ Deze gebruikersnaam is al in gebruik. Kies een andere."

        supabase.table(TABEL_NAAM).insert({
            "username": username.lower(),
            "password": hash_wachtwoord(password)
        }).execute()
        return True, "✅ Account succesvol aangemaakt! Je kunt nu inloggen."
    except Exception as e:
        return False, f"❌ Kan geen verbinding maken met de database. Probeer het later opnieuw. Details: {e}"


# --- INLOG PAGINA (Landingspagina Lay-out) ---
def login_page():
    """
    Renders the login and registration page.
    """
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

        st.divider()
        st.markdown("### 🛠️ Beschikbare Dashboards")
        st.markdown("- 🚴 **Cycling Fantasy:** Dashboard & Selectie")
        st.markdown("- 🏆 **Scorito:** Klassiekers, Evaluator & Grand Tours")
        st.markdown("- 🏁 **Sporza:** Klassiekers, Evaluator, AI Solver & Team Bouwer")

        st.markdown("<br>*Data: [Wielerorakel.nl](https://wielerorakel.nl/)*", unsafe_allow_html=True)

    with col_rechts:
        with st.container(border=True):
            st.subheader("🔒 Log in of Registreer")
            tab1, tab2 = st.tabs(["Inloggen", "Account Aanmaken"])
            
            with tab1:
                with st.form("login_form"):
                    inlog_naam = st.text_input("Gebruikersnaam", key="inlog_naam", placeholder="bijv. woutje123", help="Voer je gebruikersnaam in.")
                    inlog_ww = st.text_input("Wachtwoord", type="password", key="inlog_ww", placeholder="Jouw geheime wachtwoord", help="Voer je wachtwoord in.")
                    submitted = st.form_submit_button("Inloggen", type="primary", use_container_width=True)

                    if submitted:
                        if inlog_naam and inlog_ww:
                            with st.spinner("Aanmelden..."):
                                success = check_login(inlog_naam, inlog_ww)
                                if success:
                                    st.session_state["ingelogde_speler"] = inlog_naam.lower()
                                    st.rerun()
                                else:
                                    st.error("❌ Onjuiste gebruikersnaam, wachtwoord, of databaseverbinding mislukt.")
                        else:
                            st.warning("Vul beide velden in.")
                        
            with tab2:
                with st.form("register_form"):
                    nieuw_naam = st.text_input("Kies een Gebruikersnaam", key="nieuw_naam", placeholder="Kies een unieke naam", help="Kies een gebruikersnaam die nog niet bestaat.")
                    nieuw_ww = st.text_input("Kies een Wachtwoord", type="password", key="nieuw_ww", placeholder="Minimaal 8 tekens aanbevolen", help="Kies een sterk wachtwoord.")
                    submitted_reg = st.form_submit_button("Maak account aan", use_container_width=True)

                    if submitted_reg:
                        if nieuw_naam and nieuw_ww:
                            with st.spinner("Account aanmaken..."):
                                success, msg = create_account(nieuw_naam, nieuw_ww)
                                if success:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                        else:
                            st.warning("Vul beide velden in.")
        
        st.write("")
        if st.button("🚪 Doorgaan als gast (zonder cloud-opslag)", use_container_width=True, help="Log in als gastgebruiker. Je data wordt niet opgeslagen in de cloud."):
            st.session_state["ingelogde_speler"] = "gast"
            st.rerun()


# --- HOME PAGINA (INGELOGD) ---
def home_page():
    """
    Renders the home page for logged-in users.
    """
    speler = st.session_state.get("ingelogde_speler", "bezoeker").capitalize()
    st.write(f"# Welkom bij het Dashboard, {speler}! 🚴‍♂️")
    st.markdown("*Kies een spel in het menu aan de linkerkant om je selectie te bouwen.*")
    st.divider()
    
    if st.button("Uitloggen", type="secondary", help="Log uit en keer terug naar het inlogscherm."):
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