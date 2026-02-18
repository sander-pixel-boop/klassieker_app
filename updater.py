import streamlit as st
import pandas as pd
import unicodedata
import re
import os

st.set_page_config(page_title="PCS & News Master Sync", layout="wide")

# --- HULPFUNCTIES ---
def deep_clean(text):
    if not text: return ""
    text = str(text).lower()
    # Verwijder accenten
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Deense karakters handmatig voor Pedersen/Kragh/Bystrom
    text = text.replace('ø', 'o').replace('æ', 'ae').replace('ð', 'd')
    # Alleen letters en cijfers
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

# --- TITEL & UITLEG ---
st.title("🔄 Wieler-Updater: Nieuws + PCS")
st.markdown("""
1. Deze app laadt **bron_startlijsten.csv** (jouw handmatige nieuws-vinkjes).
2. Plak de PCS PDF-tekst om officiële vinkjes toe te voegen.
3. Download het resultaat als **startlijsten.csv** voor de hoofd-app.
""")

# --- 1. LADEN VAN DATA ---
if 'matrix' not in st.session_state:
    try:
        # We laden ALTIJD de bron als startpunt
        df_bron = pd.read_csv("bron_startlijsten.csv", sep=None, engine='python', encoding='utf-8-sig')
        name_col = 'Naam' if 'Naam' in df_bron.columns else 'NAAM'
        st.session_state['matrix'] = df_bron.set_index(name_col)
        st.success(f"✅ Basis geladen uit 'bron_startlijsten.csv' ({len(st.session_state['matrix'])} renners)")
    except Exception as e:
        st.error(f"❌ Fout: Kan 'bron_startlijsten.csv' niet vinden op GitHub. Foutmelding: {e}")
        st.stop()

# --- 2. INTERFACE ---
races = st.session_state['matrix'].columns.tolist()
race = st.selectbox("Welke koers wil je updaten met PCS data?", races)

update_mode = st.radio(
    "Update methode voor deze koers:",
    ["Vinkjes toevoegen (Behoud huidige nieuws-vinkjes)", "Kolom overschrijven (Alleen officiële PCS lijst)"],
    index=0,
    help="Kies toevoegen als je geruchten wilt behouden. Kies overschrijven als de officiële lijst definitief is."
)

plak_veld = st.text_area("Plak hier de PCS PDF/Print tekst (Ctrl+A uit de PDF):", height=250)

# --- 3. VERWERKING ---
if st.button(f"Verwerk PCS data voor {race}"):
    if plak_veld:
        # Stap A: Reset indien gewenst
        if "overschrijven" in update_mode.lower():
            st.session_state['matrix'][race] = 0
            st.info(f"Kolom {race} is leeggemaakt voor de nieuwe import.")

        # Stap B: Filter de PDF tekst op rugnummers
        regels = plak_veld.split('\n')
        pdf_regels_schoon = [deep_clean(r) for r in regels if re.search(r'\d+', r)]
        
        gevonden_count = 0
        herkende_namen = []
        matched_indices = set()

        # Stap C: Matching op namen (minimaal 2 delen van de naam moeten matchen)
        for naam in st.session_state['matrix'].index:
            schoon_naam = deep_clean(naam)
            naam_delen = [d for d in schoon_naam.split() if len(d) > 2] # Alleen betekenisvolle woorden
            
            if naam_delen:
                for idx, regel in enumerate(pdf_regels_schoon):
                    # Check hoeveel delen van de naam in de regel voorkomen
                    match_count = sum(1 for deel in naam_delen if deel in regel)
                    
                    # Logica: Alle delen moeten matchen (bij 2 delen) of minstens 2 (bij 3+ delen)
                    is_match = False
                    if len(naam_delen) <= 2 and match_count == len(naam_delen):
                        is_match = True
                    elif len(naam_delen) > 2 and match_count >= 2:
                        is_match = True

                    if is_match:
                        # Alleen als hij nog niet op 1 stond, tellen we hem als 'nieuw'
                        if st.session_state['matrix'].at[naam, race] == 0:
                            st.session_state['matrix'].at[naam, race] = 1
                            gevonden_count += 1
                        herkende_namen.append(naam)
                        matched_indices.add(idx)
                        break

        st.success(f"Klaar! {gevonden_count} nieuwe renners herkend die nog geen vinkje hadden.")
        
        # Monitor: Wie stond er in de PDF maar niet in onze database?
        missers = []
        for i, r in enumerate(regels):
            if re.search(r'\d+', r) and i not in matched_indices:
                missers.append(r.strip())
        
        if missers:
            with st.expander("⚠️ Bekijk renners uit PDF die niet in je database staan"):
                for m in missers:
                    st.text(m)

# --- 4. EXPORT ---
st.divider()
st.subheader("Huidige Tabel Preview")
st.dataframe(st.session_state['matrix'])

if st.button("💾 Genereer startlijsten.csv"):
    # We resetten de index zodat 'Naam' weer een kolom wordt in de CSV
    final_csv = st.session_state['matrix'].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download startlijsten.csv voor GitHub",
        data=final_csv,
        file_name="startlijsten.csv",
        mime="text/csv"
    )
