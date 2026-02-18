import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="Wieler Updater - Kleurcodes", layout="wide")

def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd').replace('-', ' ')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

def style_dataframe(df):
    """
    Functie om de tabel te kleuren: 
    1 = Groen, ? = Oranje
    """
    def color_cells(val):
        if val == "1":
            return 'background-color: #d4edda; color: #155724;' # Groen
        if val == "?":
            return 'background-color: #fff3cd; color: #856404;' # Oranje
        return ''
    return df.style.applymap(color_cells)

st.title("🔄 Kleur-Gecodeerde Updater")
st.info("🟢 Groen (1) = PCS Bevestigd | 🟠 Oranje (?) = Alleen Nieuws/Geruchten")

# 1. Referentie & Bron laden
try:
    df_stats = pd.read_csv("renners_stats.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_stats.columns = [c.strip().upper() for c in df_stats.columns]
    master_names = df_stats['NAAM'].tolist()
    
    df_bron = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
    name_col = 'Naam' if 'Naam' in df_bron.columns else 'NAAM'
    df_bron = df_bron.set_index(name_col)
except Exception as e:
    st.error(f"Bestanden missen: {e}")
    st.stop()

# 2. Matrix opbouw in Session State
if 'matrix_display' not in st.session_state:
    # We maken een matrix met strings om '?' te kunnen tonen
    st.session_state['matrix_display'] = pd.DataFrame("0", index=master_names, columns=df_bron.columns)
    for col in df_bron.columns:
        # Zet de huidige nieuws-vinkjes op '?'
        news_indices = df_bron[df_bron[col] == 1].index
        st.session_state['matrix_display'].loc[st.session_state['matrix_display'].index.isin(news_indices), col] = "?"

race = st.selectbox("Update koers met PCS PDF:", st.session_state['matrix_display'].columns.tolist())
plak_veld = st.text_area("Plak hier de PCS PDF tekst:", height=200)

if st.button(f"Update {race} via PDF"):
    if plak_veld:
        regels = plak_veld.split('\n')
        # Filter op regels die met een nummer beginnen (rugnummers)
        gevalideerde_regels = [deep_clean(r) for r in regels if re.match(r'^\d+', r.strip())]
        schone_tekst_bak = " ".join(gevalideerde_regels)
        
        pcs_count = 0
        for naam in st.session_state['matrix_display'].index:
            schoon_naam = deep_clean(naam)
            stopwoorden = {'van', 'den', 'der', 'de', 'het', 'ten', 'ter'}
            naam_delen = [d for d in schoon_naam.split() if d not in stopwoorden and len(d) > 2]
            
            if naam_delen:
                # Als match in PDF, wordt het een harde '1'
                if all(deel in schone_tekst_bak for deel in naam_delen):
                    st.session_state['matrix_display'].at[naam, race] = "1"
                    pcs_count += 1
        
        st.success(f"PCS Update klaar: {pcs_count} renners bevestigd (Groen).")

# 3. Tonen van de tabel
st.subheader("Huidige Status")
st.table(style_dataframe(st.session_state['matrix_display'].head(50))) # Head voor performance, gebruik dataframe voor scrollen
st.dataframe(style_dataframe(st.session_state['matrix_display']))

# 4. Export (Zet ? om naar 1 voor de hoofd-app)
st.divider()
if st.button("💾 Genereer startlijsten.csv voor de App"):
    # Voor de app.py maken we er weer overal een '1' van (zowel ? als 1)
    df_export = st.session_state['matrix_display'].replace("?", "1").replace("0", "0").astype(int)
    csv = df_export.reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download startlijsten.csv", csv, "startlijsten.csv", "text/csv")
