import streamlit as st
import pandas as pd
import plotly.express as px
import os
from thefuzz import process

# --- CONFIGURATIE ---
st.set_page_config(page_title="Sporza Model Evaluator", layout="wide", page_icon="🏁")

st.title("🏁 Sporza Model Evaluator")
st.markdown("""
Welkom bij de **Sporza Model Evaluator**. Dit dashboard vergelijkt hoe verschillende Sporza-modellen (120M budget, 20 renners) presteren. 

**Hoe het werkt:**
1. **Punten:** De officiële Sporza top-20 telling wordt gebruikt (100, 80, 70, 60, 50, 40, 36, 32, 28, 24, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2).
2. **Geen Kopmannen:** In tegenstelling tot Scorito hebben alle renners in de selectie dezelfde waarde (geen 3x of 2x multipliers).
3. **Selectie:** Punten worden berekend over de 20 renners die in het model staan.
""")

# Sporza Kalender
ALLE_KOERSEN_SPORZA = ["OML", "KBK", "SAM", "STR", "NOK", "BKC", "MSR", "RVB", "E3", "IFF", "DDV", "RVV", "SP", "PR", "RVL", "BRP", "AGT", "WAP", "LBL"]

# Sporza Puntenverdeling
SPORZA_PUNTEN = {
    1: 100, 2: 80, 3: 70, 4: 60, 5: 50, 6: 40, 7: 36, 8: 32, 9: 28, 10: 24,
    11: 20, 12: 18, 13: 16, 14: 14, 15: 12, 16: 10, 17: 8, 18: 6, 19: 4, 20: 2
}

# --- HARDCODED SPORZA TEAMS ---
# Hier kun je de teams invullen die je wilt vergelijken
SPORZA_TEAMS = {
    "AI Model Alpha": [
        "Mathieu van der Poel", "Wout van Aert", "Mads Pedersen", "Arnaud De Lie", 
        "Jasper Philipsen", "Tim Merlier", "Jonathan Milan", "Biniam Girmay",
        "Stefan Küng", "Jasper Stuyven", "Tiesj Benoot", "Oier Lazkano",
        "Nils Politt", "Toms Skujiņš", "Laurence Pithie", "Matej Mohorič",
        "Julian Alaphilippe", "Jan Tratnik", "Luca Mozzato", "Corbin Strong"
    ],
    "Sander's Sporza Team": [
        "Mathieu van der Poel", "Mads Pedersen", "Arnaud De Lie", "Jasper Philipsen",
        "Tim Merlier", "Jonathan Milan", "Stefan Küng", "Jasper Stuyven",
        "Tiesj Benoot", "Oier Lazkano", "Nils Politt", "Toms Skujiņš",
        "Laurence Pithie", "Matej Mohorič", "Jan Tratnik", "Jenno Berckmoes",
        "Vincenzo Albanese", "Axel Zingle", "Oliver Naesen", "Amaury Capiot"
    ]
}

# --- HULPFUNCTIES ---
def get_file_mod_time(filepath):
    return os.path.getmtime(filepath) if os.path.exists(filepath) else 0

@st.cache_data
def load_data(stats_mod_time):
    # We gebruiken hetzelfde stats bestand als de rest van de app
    df_stats = pd.read_csv("renners_stats.csv", sep='\t')
    if 'Naam' in df_stats.columns:
        df_stats = df_stats.rename(columns={'Naam': 'Renner'})
    alle_renners = sorted(df_stats['Renner'].dropna().unique())
    return df_stats, alle_renners

stats_time = get_file_mod_time("renners_stats.csv")
df_stats, alle_renners = load_data(stats_time)

# --- BEREKENING ---
if not os.path.exists("uitslagen.csv"):
    st.error("Bestand `uitslagen.csv` niet gevonden.")
else:
    try:
        df_raw_uitslagen = pd.read_csv("uitslagen.csv", sep=None, engine='python')
        df_raw_uitslagen.columns = [str(c).strip().title() for c in df_raw_uitslagen.columns]
        
        # Fuzzy matching voor uitslagen
        uitslag_parsed = []
        for index, row in df_raw_uitslagen.iterrows():
            koers = str(row['Race']).strip().upper()
            rank_str = str(row['Rnk']).strip().upper()
            if rank_str in ['DNS', 'NAN', '']: continue
            
            rider_name = str(row['Rider']).strip()
            beste_match, score = process.extractOne(rider_name, alle_renners)
            
            if score > 75:
                rank = int(rank_str) if rank_str.isdigit() else 999
                uitslag_parsed.append({"Koers": koers, "Rank": rank, "Renner": beste_match})
        
        df_uitslagen = pd.DataFrame(uitslag_parsed)
        
        # Match Sporza afkortingen
        mapping = {'OHN': 'OML', 'SB': 'STR', 'BDP': 'RVB', 'GW': 'IFF', 'BP': 'BRP', 'AGR': 'AGT', 'WP': 'WAP'}
        df_uitslagen['Koers'] = df_uitslagen['Koers'].replace(mapping)
        
        verreden_koersen = [k for k in ALLE_KOERSEN_SPORZA if k in df_uitslagen['Koers'].unique()]
        
        if not verreden_koersen:
            st.info("Nog geen verreden koersen gevonden voor Sporza.")
        else:
            resultaten = []
            
            for koers in verreden_koersen:
                df_k = df_uitslagen[df_uitslagen['Koers'] == koers]
                
                for model_naam, selectie in SPORZA_TEAMS.items():
                    punten_koers = 0
                    score_details = []
                    
                    for renner in selectie:
                        finish = df_k[df_k['Renner'] == renner]
                        if not finish.empty:
                            rank = finish['Rank'].values[0]
                            pts = SPORZA_PUNTEN.get(rank, 0)
                            if pts > 0:
                                punten_koers += pts
                                score_details.append({"Renner": renner, "Rank": rank, "Punten": pts})
                    
                    resultaten.append({
                        "Model": model_naam,
                        "Koers": koers,
                        "Punten": punten_koers,
                        "Details": score_details
                    })
            
            df_res = pd.DataFrame(resultaten)
            df_res['Cumulatief'] = df_res.groupby('Model')['Punten'].cumsum()

            # --- VISUALISATIE ---
            fig = px.line(df_res, x="Koers", y="Cumulatief", color="Model", markers=True, title="Verloop Sporza Punten")
            st.plotly_chart(fig, use_container_width=True)

            # Tabel met totalen
            st.subheader("🏆 Tussenstand")
            tabel_data = df_res.pivot(index='Model', columns='Koers', values='Punten')
            tabel_data['Totaal'] = tabel_data.sum(axis=1)
            st.dataframe(tabel_data.sort_values('Totaal', ascending=False), use_container_width=True)

            # Detail sectie
            st.divider()
            st.subheader("🔍 Analyse per Koers")
            gekozen_koers = st.selectbox("Kies een koers:", verreden_koersen)
            
            cols = st.columns(len(SPORZA_TEAMS))
            for i, model_naam in enumerate(SPORZA_TEAMS.keys()):
                with cols[i]:
                    st.markdown(f"**{model_naam}**")
                    data = next(item for item in resultaten if item["Model"] == model_naam and item["Koers"] == gekozen_koers)
                    if data["Details"]:
                        df_det = pd.DataFrame(data["Details"])
                        st.table(df_det.sort_values('Rank'))
                        st.write(f"**Totaal: {data['Punten']} pt**")
                    else:
                        st.write("Geen punten gescoord.")

    except Exception as e:
        st.error(f"Fout bij verwerking: {e}")

# --- OVERZICHT SELECTIES ---
st.divider()
st.subheader("📋 Gebruikte Selecties")
cols = st.columns(len(SPORZA_TEAMS))
for i, (m_name, m_riders) in enumerate(SPORZA_TEAMS.items()):
    with cols[i]:
        with st.expander(f"Bekijk selectie {m_name}"):
            for r in sorted(m_riders):
                st.write(f"- {r}")
