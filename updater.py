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

def style_df(df):
    def color_cells(val):
        if val == "1": return 'background-color: #d4edda; color: #155724;' # Groen
        if val == "?": return 'background-color: #fff3cd; color: #856404;' # Oranje
        return ''
    return df.style.applymap(color_cells)

st.title("🔄 Kleur-Gecodeerde Updater")
st.info("🟢 Groen (1) = PCS Bevestigd | 🟠 Oranje (?) = Alleen Nieuws/Geruchten")

# 1. Bestanden laden
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

# 2. Matrix initialiseren
if 'matrix_display' not in st.session_state:
    st.session_state['matrix_display'] = pd.DataFrame("0", index=master_names, columns=df_bron.columns)
    for col in df_bron.columns:
        news_indices = df_bron[df_bron[col] == 1].index
        st.session_state['matrix_display'].loc[st.session_state['matrix_display'].index.isin(news_indices), col] = "?"

race = st.selectbox("Update koers via PCS PDF:", st.session_state['matrix_display'].columns.tolist())
plak_veld = st.text_area("Plak hier de PCS PDF tekst:", height=200)

if st.button(f"Update {race}"):
    if plak_veld:
        regels = plak_veld.split('\n')
        gevalideerde_regels = [deep_clean(r) for r in regels if re.match(r'^\d+', r.strip())]
        tekst_bak = " ".join(gevalideerde_regels)
        
        for naam in st.session_state['matrix_display'].index:
            schoon_naam = deep_clean(naam)
            naam_delen = [d for d in schoon_naam.split() if len(d) > 2 and d not in {'van', 'den', 'der', 'de'}]
            if naam_delen and all(deel in tekst_bak for deel in naam_delen):
                st.session_state['matrix_display'].at[naam, race] = "1"
        st.success(f"Update voor {race} voltooid.")

st.dataframe(style_df(st.session_state['matrix_display']), height=400)

if st.button("💾 Genereer startlijsten.csv"):
    # Export-logica: ? wordt 2, 1 blijft 1, rest 0
    df_export = st.session_state['matrix_display'].replace("?", "2").astype(int)
    csv = df_export.reset_index().to_csv(index=False).encode('utf-8')
    st.download_button("Download voor App", csv, "startlijsten.csv", "text/csv")
