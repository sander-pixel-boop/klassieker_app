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
        st.markdown("")
        st.markdown("- **Sporza** (Giro d'Italia)")
        st.markdown("")

        st.divider()
        st.markdown("### 🧠 Features")
        st.markdown("✅ Wiskundige AI Solvers (Knapsack optimalisatie)\n✅ Verwachte Waarde (EV) berekeningen op basis van parcours\n✅ Dynamische wissel- en transferstrategieën\n✅ Live Model Evaluator")

        st.divider()
        st.markdown("### 🛠️ Beschikbare Dashboards")
        st.markdown("")
        st.markdown("")
        st.markdown("- 🏁 **Sporza Giro:** AI Solver, Team Bouwers & Evaluator")

        st.markdown("<br>*Data: [Wielerorakel.nl](https://wielerorakel.nl/)*", unsafe_allow_html=True)

    with col_rechts:
        with st.container(border=True):
            st.subheader("🔒 Log in")

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

        st.write("")
        if st.button("🚪 Doorgaan als gast (zonder cloud-opslag)", use_container_width=True):
            st.session_state["ingelogde_speler"] = "gast"
            st.rerun()

# --- NAVIGATIE INSTELLEN ---
login = st.Page(login_page, title="Inloggen", icon="🔒")

# Sporza Grand Tour opties
sporza_giro_bouwer_c5 = st.Page("pages/Sporza/Giro/Bouwer_Concept5.py", title="Giro: Bouwer", icon="💡", url_path="sporza_giro_bouwer_c5", default=True)

# --- KEUZE: WEL OF NIET INGELOGD ---
if "ingelogde_speler" not in st.session_state:
    pg = st.navigation([login], position="hidden")
else:
    pg = st.navigation([sporza_giro_bouwer_c5], position="hidden")

pg.run()
