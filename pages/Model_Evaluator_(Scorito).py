import streamlit as st
import pandas as pd
import plotly.express as px
import os
from thefuzz import process, fuzz
import unicodedata

# --- CONFIGURATIE ---
st.set_page_config(page_title="Model Evaluator", layout="wide", page_icon="📊")

st.title("📊 Scorito Model Evaluator")
st.markdown("""
Welkom bij de **Model Evaluator**. Dit dashboard test en vergelijkt live hoe verschillende wiskundige Scorito-modellen presteren in de praktijk. Deze modellen worden afgezet tegen een door een mens samengestelde referentieselectie (*Sander's Team*).

**Hoe het werkt:**
1. Gestarte renners en daadwerkelijke uitslagen worden automatisch verwerkt via het koersverloop.
2. Voor de rekenmodellen kiest het algoritme per koers de beste drie gestarte kopmannen op basis van data en statistieken.
3. Voor de referentieselectie (*Sander's Team*) worden vooraf vastgestelde kopmannen gebruikt.
4. Na elke race worden de individuele punten en teampunten berekend op basis van de renners die **op dat moment** in de actieve selectie zaten.
""")

# Aangepast naar officiële Scorito afkortingen (BDP ipv RVB, GW ipv IFF)
ALLE_KOERSEN = ['OHN', 'KBK', 'SB', 'PN', 'TA', 'MSR', 'BDP', 'E3', 'GW', 'DDV', 'RVV', 'SP', 'PR', 'BP', 'AGR', 'WP', 'LBL']
STAT_MAPPING = {'OHN':'COB','KBK':'SPR','SB':'HLL','PN':'HLL/MTN','TA':'SPR','MSR':'AVG','BDP':'SPR','E3':'COB','GW':'SPR','DDV':'COB','RVV':'COB','SP':'SPR','PR':'COB','BP':'HLL','AGR':'HLL','WP':'HLL','LBL':'HLL'}

SCORITO_PUNTEN = {
    1: 100, 2: 90, 3: 80, 4: 70, 5: 64, 6: 60, 7: 56, 8: 52, 9: 48, 10: 44,
    11: 40, 12: 36, 13: 32, 14: 28, 15: 24, 16: 20, 17: 16, 18: 12, 19: 8, 20: 4
}
TEAMPUNTEN = {1: 30, 2: 20, 3: 10}

# --- HARDCODED TEAMS & TRANSFERS ---
HARDCODED_TEAMS = {
    "Rekenmodel 1": {
        "Start": ["Tadej Pogačar", "Mathieu van der Poel", "Jonathan Milan", "Tim Merlier", "Tim Wellens", "Dylan Groenewegen", "Stefan Küng", "Mattias Skjelmose", "Jasper Stuyven", "João Almeida", "Toms Skujiņš", "Mike Teunissen", "Isaac del Toro", "Jonas Vingegaard", "Jonas Abrahamsen", "Julian Alaphilippe", "Marc Hirschi", "Jasper Philipsen", "Mads Pedersen", "Florian Vermeersch"],
        "Transfers": [
            {"uit": "Tim Wellens", "in": "Romain Grégoire", "moment": "KBK"},
            {"uit": "Jonathan Milan", "in": "Remco Evenepoel", "moment": "PR"},
            {"uit": "Tim Merlier", "in": "Tom Pidcock", "moment": "PR"}
        ]
    },
    "Rekenmodel 2": {
        "Start": ["Tadej Pogačar", "Mads Pedersen", "Jonathan Milan", "Arnaud De Lie", "Tim Merlier", "Tim Wellens", "Dylan Groenewegen", "Mattias Skjelmose", "Florian Vermeersch", "Toms Skujiņš", "Mike Teunissen", "Marijn van den Berg", "Laurence Pithie", "Jonas Abrahamsen", "Vincenzo Albanese", "Jenno Berckmoes", "Oliver Naesen", "Mathieu van der Poel", "Jasper Philipsen", "Jasper Stuyven"],
        "Transfers": [
            {"uit": "Tim Wellens", "in": "Romain Grégoire", "moment": "KBK"},
            {"uit": "Arnaud De Lie", "in": "Remco Evenepoel", "moment": "PR"},
            {"uit": "Jasper Philipsen", "in": "Tom Pidcock", "moment": "PR"}
        ]
    },
    "Rekenmodel 3": {
        "Start": ["Tadej Pogačar", "Mathieu van der Poel", "Jasper Philipsen", "Tim Merlier", "Tim Wellens", "Dylan Groenewegen", "Mattias Skjelmose", "Florian Vermeersch", "Toms Skujiņš", "Mike Teunissen", "Isaac del Toro", "Jonas Vingegaard", "Laurence Pithie", "Gianni Vermeersch", "Jonas Abrahamsen", "Julian Alaphilippe", "Quinten Hermans", "Mads Pedersen", "Jonathan Milan", "Arnaud De Lie"],
        "Transfers": [
            {"uit": "Tim Wellens", "in": "Romain Grégoire", "moment": "KBK"},
            {"uit": "Mathieu van der Poel", "in": "Remco Evenepoel", "moment": "PR"},
            {"uit": "Dylan Groenewegen", "in": "Tom Pidcock", "moment": "PR"}
        ]
    },
    "Rekenmodel 4": {
        "Start": ["Tadej Pogačar", "Mathieu van der Poel", "Mads Pedersen", "Jonathan Milan", "Tim Wellens", "Paul Magnier", "Dylan Groenewegen", "Mattias Skjelmose", "Jasper Stuyven", "João Almeida", "Toms Skujiņš", "Mike Teunissen", "Jonas Vingegaard", "Giulio Ciccone", "Gianni Vermeersch", "Jonas Abrahamsen", "Marc Hirschi", "Jasper Philipsen", "Tim Merlier", "Isaac del Toro"],
        "Transfers": [
            {"uit": "Tim Wellens", "in": "Romain Grégoire", "moment": "KBK"},
            {"uit": "Tim Merlier", "in": "Remco Evenepoel", "moment": "PR"},
            {"uit": "Mads Pedersen", "in": "Tom Pidcock", "moment": "PR"}
        ]
    },
    "Sander's Team": {
        "Start": ["Tadej Pogačar", "Jonathan Milan", "Tom Pidcock", "Christophe Laporte", "Tim Wellens", "Paul Magnier", "Romain Grégoire", "Mattias Skjelmose", "Jasper Stuyven", "Florian Vermeersch", "Milan Fretin", "Jordi Meeus", "Toms Skujiņš", "Mike Teunissen", "Jonas Vingegaard", "Gianni Vermeersch", "Jonas Abrahamsen", "Mathieu van der Poel", "Jasper Philipsen", "Laurence Pithie"],
        "Transfers": [
            {"uit": "Mathieu van der Poel", "in": "Remco Evenepoel", "moment": "PR"},
            {"uit": "Jasper Philipsen", "in": "Ben Healy", "moment": "PR"},
            {"uit": "Laurence Pithie", "in": "Marc Hirschi", "moment": "PR"}
        ]
    }
}

# Vaste kopmannen per koers voor de referentieselectie
MIJN_EIGEN_KOPMANNEN = {
    "OHN": {"C1": "Mathieu van der Poel", "C2": "Tom Pidcock", "C3": "Tim Wellens"},
    "KBK": {"C1": "Jonathan Milan", "C2": "Jasper Philipsen", "C3": "Jordi Meeus"},
}

# --- HULPFUNCTIES VOOR NAAM-MATCHING ---
def normalize_name_logic(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def match_uitslag_naam(naam, alle_renners):
    naam_norm = normalize_name_logic(naam)
    bekende_gevallen = {
        "philipsen": "jasper philipsen",
        "pedersen": "mads pedersen",
        "pidcock": "thomas pidcock",
        "van aert": "wout van aert", 
        "van der poel": "mathieu van der poel",
        "pogacar": "tadej pogacar",
        "de lie": "arnaud de lie"
    }
    
    for key, correct in bekende_gevallen.items():
        if key in naam_norm:
            for target in alle_renners:
                if correct in normalize_name_logic(target):
                    return target
                
    bests = process.extractBests(naam_norm, alle_renners, scorer=fuzz.token_set_ratio, limit=5)
    if bests and bests[0][1] >= 75:
        top_score = bests[0][1]
        candidates = [b[0] for b in bests if b[1] >= top_score - 3]
        candidates.sort(key=lambda x: (abs(len(normalize_name_logic(x)) - len(naam_norm)), -fuzz.ratio(naam_norm, normalize_name_logic(x))))
        return candidates[0]
    return naam

def get_file_mod_time(filepath):
    return os.path.getmtime(filepath) if os.path.exists(filepath) else 0

@st.cache_data
def load_data(stats_mod_time):
    df_stats = pd.read_csv("renners_stats.csv", sep='\t')
    if 'Naam' in df_stats.columns:
        df_stats = df_stats.rename(columns={'Naam': 'Renner'})
    alle_renners = sorted(df_stats['Renner'].dropna().unique())
    return df_stats, alle_renners

stats_time = get_file_mod_time("renners_stats.csv")
df_stats, alle_renners = load_data(stats_time)

st.divider()

# --- GRAFIEK EN BEREKENING ---
if not os.path.exists("uitslagen.csv"):
    st.error("Bestand `uitslagen.csv` niet gevonden. Zorg dat dit bestand in de hoofddirectory staat.")
else:
    try:
        df_raw_uitslagen = pd.read_csv("uitslagen.csv", sep='\t', engine='python')
    except Exception as e:
        try:
             df_raw_uitslagen = pd.read_csv("uitslagen.csv", sep=None, engine='python')
        except Exception as e2:
             st.error(f"Fout bij inlezen van uitslagen.csv: {e2}")
             st.stop()
             
    df_raw_uitslagen.columns = [str(c).strip().title() for c in df_raw_uitslagen.columns]

    if 'Race' not in df_raw_uitslagen.columns or 'Rnk' not in df_raw_uitslagen.columns or 'Rider' not in df_raw_uitslagen.columns:
        st.error("Het bestand uitslagen.csv mist de vereiste kolommen: Race, Rnk, Rider.")
    else:
        sporza_naar_scorito_map = {
            'OML': 'OHN', 'STR': 'SB', 'RVB': 'BDP', 
            'IFF': 'GW', 'BRP': 'BP', 'AGT': 'AGR', 'WAP': 'WP'
        }
        
        uitslag_parsed = []
        for index, row in df_raw_uitslagen.iterrows():
            koers_origineel = str(row['Race']).strip().upper()
            
            # Pas hier direct de mapping toe zodat de eerste koersen wél matchen!
            koers = sporza_naar_scorito_map.get(koers_origineel, koers_origineel)
            
            rank_str = str(row['Rnk']).strip().upper()
            if rank_str in ['DNS', 'NAN', '']:
                continue 
                
            rider_name = str(row['Rider']).strip()
            gekoppelde_naam = match_uitslag_naam(rider_name, alle_renners)
            
            rank = int(rank_str) if rank_str.isdigit() else 999 
            uitslag_parsed.append({
                "Koers": koers, 
                "Rank": rank, 
                "Renner": gekoppelde_naam
            })
                        
        df_uitslagen = pd.DataFrame(uitslag_parsed)
        
        if df_uitslagen.empty:
            st.error("Kon geen enkele renner succesvol matchen. Controleer of de namen in uitslagen.csv kloppen.")
            st.stop()

        verreden_koersen = [k for k in ALLE_KOERSEN if k in df_uitslagen['Koers'].unique()]
        
        if not verreden_koersen:
            st.info("Nog geen geldige koersen gevonden in de dataset.")
        else:
            resultaten_lijst = []
            details_lijst = []

            for koers in verreden_koersen:
                koers_stat = STAT_MAPPING.get(koers, "COB")
                df_koers_uitslag = df_uitslagen[df_uitslagen['Koers'] == koers]
