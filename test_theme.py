import streamlit as st

st.set_page_config(page_title="Test Theme", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Titillium Web', sans-serif;
}

/* Main background */
[data-testid="stAppViewContainer"] {
    background-color: #0b0514;
    background-image: radial-gradient(circle at 50% 0%, #2b1154 0%, #0b0514 60%);
    color: white;
}

[data-testid="stHeader"] {
    background-color: transparent;
}

h1, h2, h3 {
    color: white !important;
    font-family: 'Titillium Web', sans-serif !important;
    text-transform: uppercase;
}

h1 { font-weight: 900 !important; }
h2, h3 { font-weight: 700 !important; }

/* Let paragraphs stay normal */
p {
    font-family: 'Titillium Web', sans-serif !important;
    color: #dcdcdc;
}

/* Primary buttons */
button[kind="primary"] {
    background-color: #f672ff !important;
    color: white !important;
    font-weight: 900 !important;
    border: none !important;
    text-transform: uppercase;
    border-radius: 4px !important;
}
button[kind="primary"]:hover {
    background-color: #e55ce0 !important;
}

/* Secondary buttons */
button[kind="secondary"] {
    background-color: rgba(43, 17, 84, 0.7) !important;
    color: white !important;
    border: 1px solid #4a2c7a !important;
    font-weight: 700 !important;
}
button[kind="secondary"]:hover {
    border-color: #f672ff !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background-color: #1a0b2e !important;
    border: 1px solid #4a2c7a !important;
    border-radius: 8px !important;
}

[data-testid="stExpander"] > details > summary {
    background-color: #240f40 !important;
}

[data-testid="stExpander"] > details > summary p {
    color: white !important;
    font-weight: 700 !important;
    text-transform: uppercase;
}

/* Metric boxes */
[data-testid="stMetricValue"] {
    font-weight: 900 !important;
    color: #f672ff !important;
}

[data-testid="stMetricLabel"] {
    color: white !important;
    text-transform: uppercase;
}

</style>
""", unsafe_allow_html=True)

st.title("Giro Team Bouwer - Simpel & Intuïtief")
st.markdown("Selecteer je 16 renners voor de Giro d'Italia. Klik op de checkbox om een renner toe te voegen of te verwijderen.")

col_stat1, col_stat2, col_stat3 = st.columns(3)
col_stat1.metric("Geselecteerde Renners", "10 / 16")
col_stat2.metric("Budget Resterend", "€ 40.0M")
col_stat3.metric("Verwachte Waarde (EV)", "120.0")

st.button("💾 Sla Team Op", type="primary", use_container_width=True)
st.button("➕ Wout van Aert\n€10.0M", use_container_width=True)

with st.expander("Etappe 1: Vlak"):
    st.markdown("💡 Top 5 Suggesties voor deze etappe:")
