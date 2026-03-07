import streamlit as st
import pandas as pd
import plotly.express as px
import os
from thefuzz import process

# --- CONFIGURATIE ---
st.set_page_config(page_title="Sporza Model Evaluator", layout="wide", page_icon="🏁")

st.title("🏁 Sporza Model Evaluator")
st.markdown("""
Vergelijk de prestaties van de verschillende Sporza-methodieken en het team van Sander. 
Inclusief de officiële 1-kopman regel (dubbele punten).
""")

# Sporza Kalender & Punten
ALLE_KOERSEN_SPORZA = ["OML", "KBK", "SAM", "STR", "NOK", "BKC", "MSR", "RVB", "E3", "IFF", "DDV", "RVV", "SP", "PR", "RVL", "BRP", "AGT", "WAP", "LBL"]
STAT_MAPPING = {"OML": "COB", "KBK": "SPR", "SAM": "SPR", "STR": "HLL", "NOK": "SPR", "BKC": "SPR", "MSR": "AVG", "RVB": "SPR", "E3": "COB", "IFF": "SPR", "DDV": "COB", "RVV": "COB", "SP": "SPR", "PR": "COB", "RVL": "SPR", "BRP": "HLL", "AGT": "HLL", "WAP": "HLL", "LBL": "HLL"}

SPORZA_PUNTEN = {
    1: 100, 2: 80, 3: 70, 4: 60, 5: 50, 6: 40, 7: 36, 8: 32, 9: 28, 10: 24,
    11: 20, 12: 18, 13: 16, 14: 14, 15: 12, 16: 10, 17: 8, 18: 6, 19: 4, 20: 2
}

# --- HARDCODED SPORZA TEAMS ---
SPORZA_TEAMS = {
    "Sporza Methode 1": {
        "Start": ["Mathieu van der Poel", "Tadej Pogačar", "Jasper Philipsen", "Tim Merlier", "Jonathan Milan", "Tim Wellens", "Jasper Stuyven", "Florian Vermeersch", "Jordi Meeus", "Biniam Girmay", "Romain Grégoire", "Milan Fretin", "Toms Skujiņš", "Dylan Groenewegen", "Jonas Abrahamsen", "Pavel Bittner", "Gianni Vermeersch", "Mike Teunissen", "Fred Wright", "Stanislaw Aniolkowski"],
        "Transfers": [
            {"uit": "Mathieu van der Poel", "in": "Tom Pidcock", "moment": "PR"},
            {"uit": "Jordi Meeus", "in": "Marc Hirschi", "moment": "PR"},
            {"uit": "Jasper Philipsen", "in": "Mattias Skjelmose", "moment": "PR"},
            {"uit": "Tim Merlier", "in": "Ben Healy", "moment": "PR"},
            {"uit": "Jonathan Milan", "in": "Remco Evenepoel", "moment": "PR"}
        ]
    },
    "Sporza Methode 2": {
        "Start": ["Mathieu van der Poel", "Tadej Pogačar", "Jasper Philipsen", "Tom Pidcock", "Tim Merlier", "Matteo Jorgenson", "Florian Vermeersch", "Jordi Meeus", "Søren Wærenskjold", "Romain Grégoire", "Milan Fretin", "Dries De Bondt", "Quinten Hermans", "Toms Skujiņš", "Dylan Groenewegen", "Jonas Abrahamsen", "Julian Alaphilippe", "Gianni Vermeersch", "Mike Teunissen", "Fred Wright"],
        "Transfers": [
            {"uit": "Mathieu van der Poel", "in": "Remco Evenepoel", "moment": "PR"},
            {"uit": "Florian Vermeersch", "in": "Mattias Skjelmose", "moment": "PR"},
            {"uit": "Jasper Philipsen", "in": "Giulio Ciccone", "moment": "PR"},
            {"uit": "Jordi Meeus", "in": "Ben Healy", "moment": "PR"},
            {"uit": "Tim Merlier", "in": "Marc Hirschi", "moment": "PR"}
        ]
    },
    "Sander's Team": {
        "Start": ["Mathieu van der Poel", "Tadej Pogačar", "Wout van Aert", "Jasper Philipsen", "Jonathan Milan", "Jasper Stuyven", "Florian Vermeersch", "Jordi Meeus", "Biniam Girmay", "Romain Grégoire", "Milan Fretin", "Toms Skujiņš", "Jonas Abrahamsen", "Julian Alaphilippe", "Pavel Bittner", "Gianni Vermeersch", "Mike Teunissen", "Fred Wright", "Alexis Renard", "Stanislaw Aniolkowski"],
        "Transfers": [
            {"uit": "Jasper Philipsen", "in": "Ben Healy", "moment": "PR"},
            {"uit": "Jonathan Milan", "in": "Tom Pidcock", "moment": "PR"},
            {"uit": "Wout van Aert", "in": "Marc Hirschi", "moment": "PR"},
            {"uit": "Florian Vermeersch", "in": "Mattias Skjelmose", "moment": "PR"},
            {"uit": "Mathieu van der Poel", "in": "Remco Evenepoel", "moment": "PR"}
        ]
    }
}

MIJN_EIGEN_KOPMANNEN = {
    "OML": "Mathieu van der Poel",
    "KBK": "Jonathan Milan",
    "STR": "Tadej Pogačar"
    # Voeg hier handmatig je kopmannen per koers toe!
}

# --- DATA LADEN ---
@st.cache_data
def load_base_data():
    df_stats = pd.read_csv("renners_stats.csv", sep='\t')
    if 'Naam' in df_stats.columns: df_stats = df_stats.rename(columns={'Naam': 'Renner'})
    return df_stats, sorted(df_stats['Renner'].dropna().unique())

df_stats, alle_renners = load_base_data()

# --- VERWERKING ---
if not os.path.exists("uitslagen.csv"):
    st.error("Bestand `uitslagen.csv` niet gevonden.")
else:
    df_raw = pd.read_csv("uitslagen.csv", sep=None, engine='python')
    df_raw.columns = [str(c).strip().title() for c in df_raw.columns]
    
    uitslag_parsed = []
    for _, row in df_raw.iterrows():
        koers = str(row['Race']).strip().upper()
        rank_str = str(row['Rnk']).strip().upper()
        if rank_str in ['DNS', 'NAN', '']: continue
        match, score = process.extractOne(str(row['Rider']).strip(), alle_renners)
        if score > 75:
            uitslag_parsed.append({"Koers": koers, "Rank": int(rank_str) if rank_str.isdigit() else 999, "Renner": match})
    
    df_uitslagen = pd.DataFrame(uitslag_parsed)
    mapping = {'OHN': 'OML', 'SB': 'STR', 'BDP': 'RVB', 'GW': 'IFF', 'BP': 'BRP', 'AGR': 'AGT', 'WP': 'WAP'}
    df_uitslagen['Koers'] = df_uitslagen['Koers'].replace(mapping)
    
    verreden = [k for k in ALLE_KOERSEN_SPORZA if k in df_uitslagen['Koers'].unique()]
    
    if verreden:
        resultaten = []
        details_lijst = []
        for koers in verreden:
            df_k = df_uitslagen[df_uitslagen['Koers'] == koers]
            idx_curr = ALLE_KOERSEN_SPORZA.index(koers)
            
            for m_naam, m_data in SPORZA_TEAMS.items():
                actieve_sel = list(m_data["Start"])
                for t in m_data.get("Transfers", []):
                    if idx_curr > ALLE_KOERSEN_SPORZA.index(t["moment"]):
                        if t["uit"] in actieve_sel: actieve_sel.remove(t["uit"])
                        if t["in"] not in actieve_sel: actieve_sel.append(t["in"])
                
                # Kopman bepalen
                kopman = None
                if m_naam == "Sander's Team":
                    kopman_intended = MIJN_EIGEN_KOPMANNEN.get(koers)
                    if kopman_intended in actieve_sel:
                        kopman = kopman_intended
                
                if not kopman:
                    koers_stat = STAT_MAPPING.get(koers, "COB")
                    team_stats = df_stats[df_stats['Renner'].isin(actieve_sel)].copy()
                    team_stats = team_stats.sort_values(by=koers_stat, ascending=False).reset_index(drop=True)
                    if not team_stats.empty:
                        kopman = team_stats.iloc[0]['Renner']
                
                punten_k = 0
                for renner in actieve_sel:
                    f = df_k[df_k['Renner'] == renner]
                    if not f.empty:
                        rank = f['Rank'].values[0]
                        pts = SPORZA_PUNTEN.get(rank, 0)
                        is_kopman = (renner == kopman)
                        
                        if is_kopman:
                            pts *= 2
                        
                        punten_k += pts
                        details_lijst.append({
                            "Koers": koers, "Model": m_naam, "Renner": renner,
                            "Kopman": "✅" if is_kopman else "-",
                            "Rank": rank, "Punten": pts
                        })
                
                resultaten.append({
                    "Model": m_naam, "Koers": koers, "Punten": punten_k, "Kopman": kopman
                })
        
        df_res = pd.DataFrame(resultaten)
        df_res['Cumulatief'] = df_res.groupby('Model')['Punten'].cumsum()
        
        st.plotly_chart(px.line(df_res, x="Koers", y="Cumulatief", color="Model", markers=True), use_container_width=True)
        
        st.subheader("🏆 Tussenstand")
        tabel = df_res.pivot(index='Model', columns='Koers', values='Punten')
        tabel['Totaal'] = tabel.sum(axis=1)
        st.dataframe(tabel.sort_values('Totaal', ascending=False), use_container_width=True)

        st.divider()
        st.subheader("🔍 Analyse per Koers")
        gekozen_koers = st.selectbox("Kies een koers:", verreden)
        
        cols = st.columns(len(SPORZA_TEAMS))
        for i, model_naam in enumerate(SPORZA_TEAMS.keys()):
            with cols[i]:
                st.markdown(f"**{model_naam}**")
                data_k = df_res[(df_res['Model'] == model_naam) & (df_res['Koers'] == gekozen_koers)]
                kopman_naam = data_k['Kopman'].values[0] if not data_k.empty else "-"
                st.write(f"🎯 Kopman: **{kopman_naam}**")
                
                df_det = pd.DataFrame(details_lijst)
                if not df_det.empty:
                    df_det_koers = df_det[(df_det['Koers'] == gekozen_koers) & (df_det['Model'] == model_naam)]
                    if not df_det_koers.empty:
                        st.dataframe(df_det_koers[['Renner', 'Kopman', 'Rank', 'Punten']].sort_values('Punten', ascending=False), hide_index=True)
                        st.write(f"**Totaal: {data_k['Punten'].values[0]} pt**")
                    else:
                        st.write("Geen renners in de uitslag.")

# --- OVERZICHT SELECTIES ---
st.divider()
st.subheader("📋 Gebruikte Selecties")
cols = st.columns(len(SPORZA_TEAMS))
for i, (m_name, m_data) in enumerate(SPORZA_TEAMS.items()):
    with cols[i]:
        with st.expander(f"Team: {m_name}"):
            st.markdown("**Start-Team (20)**")
            for r in sorted(m_data["Start"]): st.write(f"- {r}")
            st.markdown("**Transfers**")
            for t in m_data.get("Transfers", []):
                st.write(f"Wissel na **{t['moment']}**: ❌ {t['uit']} 📥 {t['in']}")
