import streamlit as st
from app_utils.db import init_connection
from app_utils.crypto import hash_wachtwoord, verify_wachtwoord

st.set_page_config(page_title="Wieler Spellen Solver", page_icon="🚴‍♂️", layout="wide")

# --- DATABASE CONNECTIE ---
supabase = init_connection()
TABEL_NAAM = st.secrets.get("TABEL_NAAM", "gebruikers_data_test")

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
                    inlog_naam = st.text_input("Gebruikersnaam", key="inlog_naam", placeholder="bijv. woutje123", help="Voer je accountnaam in om in te loggen.")
                    inlog_ww = st.text_input("Wachtwoord", type="password", key="inlog_ww", placeholder="Jouw geheime wachtwoord", help="Voer het wachtwoord van je account in.")
                    submitted = st.form_submit_button("Inloggen", type="primary", use_container_width=True)

                    if submitted:
                        if inlog_naam and inlog_ww:
                            with st.spinner("Aanmelden..."):
                                try:
                                    res = supabase.table(TABEL_NAAM).select("password").eq("username", inlog_naam.lower()).execute()
                                    if res.data:
                                        db_password = res.data[0].get("password")
                                        if verify_wachtwoord(inlog_ww, db_password):
                                            # Upgrade legacy SHA-256 hash to PBKDF2 hash automatically
                                            if not db_password.startswith("pbkdf2_sha256$"):
                                                new_hash = hash_wachtwoord(inlog_ww)
                                                supabase.table(TABEL_NAAM).update({"password": new_hash}).eq("username", inlog_naam.lower()).execute()

                                            st.session_state["ingelogde_speler"] = inlog_naam.lower()
                                            st.rerun()
                                        else:
                                            st.error("❌ Onjuiste gebruikersnaam of wachtwoord.")
                                    else:
                                        st.error("❌ Onjuiste gebruikersnaam of wachtwoord.")
                                except Exception as e:
                                    if "Name or service not known" in str(e) or "Invalid URL" in str(e) or "ConnectError" in str(e):
                                        st.error("❌ Database configuratie ontbreekt of is ongeldig. Controleer je `.streamlit/secrets.toml` of klik op 'Doorgaan als gast'.")
                                    else:
                                        st.error(f"❌ Kan geen verbinding maken met de database. Probeer het later opnieuw. Error: {e}")
                        else:
                            st.warning("Vul beide velden in.")
                        
            with tab2:
                with st.form("register_form"):
                    nieuw_naam = st.text_input("Kies een Gebruikersnaam", key="nieuw_naam", placeholder="Kies een unieke naam", help="Kies een unieke gebruikersnaam voor je account.")
                    nieuw_ww = st.text_input("Kies een Wachtwoord", type="password", key="nieuw_ww", placeholder="Minimaal 8 tekens aanbevolen", help="Kies een sterk wachtwoord voor je account.")
                    submitted_reg = st.form_submit_button("Maak account aan", use_container_width=True)

                    if submitted_reg:
                        if nieuw_naam and nieuw_ww:
                            with st.spinner("Account aanmaken..."):
                                try:
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
                                except Exception as e:
                                    if "Name or service not known" in str(e) or "Invalid URL" in str(e) or "ConnectError" in str(e):
                                        st.error("❌ Database configuratie ontbreekt of is ongeldig. Controleer je `.streamlit/secrets.toml` of klik op 'Doorgaan als gast'.")
                                    else:
                                        st.error(f"❌ Kan geen verbinding maken met de database. Probeer het later opnieuw. Error: {e}")
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
cf_pagina = st.Page("pages/Cycling_Fantasy/Classics/Dashboard.py", title="CF Dashboard", icon="🚴", url_path="cf_dashboard")

# Scorito pagina's
scorito_klassiekers = st.Page("pages/Scorito/Classics/Klassiekers.py", title="Klassiekers", icon="🏆", url_path="scorito_klassiekers")
scorito_evaluator = st.Page("pages/Scorito/Classics/Evaluator.py", title="Evaluator", icon="📊", url_path="scorito_evaluator")
scorito_giro = st.Page("pages/Scorito/Giro/scorito_giro_team_bouwer.py", title="Giro d'Italia", icon="🇮🇹", url_path="scorito_giro")

# Sporza pagina's
sporza_klassiekers = st.Page("pages/Sporza/Classics/Klassiekers.py", title="Klassiekers", icon="🏁", url_path="sporza_klassiekers")
sporza_evaluator = st.Page("pages/Sporza/Classics/Evaluator.py", title="Evaluator", icon="📊", url_path="sporza_evaluator")

# Sporza Grand Tour opties
sporza_giro_ai = st.Page("pages/Sporza/Giro/AI_Solver.py", title="Giro: AI Solver", icon="🤖", url_path="sporza_giro_ai")
sporza_giro_bouwer = st.Page("pages/Sporza/Giro/Team_Bouwer.py", title="Giro: Bouwer C1", icon="🛠️", url_path="sporza_giro_bouwer")
sporza_giro_bouwer_c1 = st.Page("pages/Sporza/Giro/Bouwer_Concept1.py", title="Giro: Bouwer C2", icon="🗂️", url_path="sporza_giro_bouwer_c1")
sporza_giro_bouwer_c2 = st.Page("pages/Sporza/Giro/Bouwer_Concept2.py", title="Giro: Bouwer C3", icon="🪄", url_path="sporza_giro_bouwer_c2")
sporza_giro_bouwer_c3 = st.Page("pages/Sporza/Giro/Bouwer_Concept3.py", title="Giro: Bouwer C4", icon="✂️", url_path="sporza_giro_bouwer_c3")
sporza_giro_evaluator = st.Page("pages/Sporza/Giro/Evaluator.py", title="[Beta] Giro: Evaluator", icon="📊", url_path="sporza_giro_evaluator")

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
        "Sporza - Grand Tours": [sporza_giro_bouwer, sporza_giro_bouwer_c1, sporza_giro_bouwer_c2, sporza_giro_bouwer_c3, sporza_giro_evaluator]
    })

pg.run()
