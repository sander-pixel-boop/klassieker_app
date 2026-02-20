import streamlit as st
import pandas as pd
import pulp
from thefuzz import process, fuzz

# --- CONFIGURATIE ---
st.set_page_config(page_title="Klassiekers Solver 2026", layout="wide", page_icon="🚴‍♂️")

# --- DATA LADEN & MERGEN ---
@st.cache_data
def load_and_merge_data():
    # Lees bestanden in
    # Let op: als je renners_stats.csv als komma-gescheiden hebt opgeslagen, verander sep='\t' naar sep=','
    df_prog = pd.read_csv("bron_startlijsten.csv")
    df_stats = pd.read_csv("renners_stats.csv", sep='\t') 
    
    # Zorg dat de naamkolom in stats 'Renner' heet
    if 'Naam' in df_stats.columns:
        df_stats = df_stats.rename(columns={'Naam': 'Renner'})
    
    # 1. Haal unieke namen op
    short_names = df_prog['Renner'].unique()
    full_names = df_stats['Renner'].unique()
    
    # 2. Maak een fuzzy mapping dictionary
    name_mapping = {}
    
    # Handmatige overrides voor afkortingen of namen die fout kunnen gaan
    manual_overrides = {
        "Poel": "Mathieu van der Poel",
        "Aert": "Wout van Aert",
        "Lie": "Arnaud De Lie",
        "Gils": "Maxim Van Gils",
        "Berg": "Marijn van den Berg",
        "Broek": "Frank van den Broek"
    }
    
    for short in short_names:
        if short in manual_overrides:
            name_mapping[short] = manual_overrides[short]
        else:
            # Fuzzy match op basis van token_set_ratio
            best_match, score = process.extractOne(short, full_names, scorer=fuzz.token_set_ratio)
            name_mapping[short] = best_match

    # 3. Voer de mapping uit op de startlijst
    df_prog['Ren
