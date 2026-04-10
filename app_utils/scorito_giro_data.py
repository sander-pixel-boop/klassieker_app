import pandas as pd
import os
import streamlit as st
from app_utils.name_matching import match_naam_slim, normalize_name_logic

@st.cache_data
def load_giro_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prijzen_file = os.path.join(base_dir, "data", "giro262", "scorito_giro26_startlijst.csv")
    stats_file   = os.path.join(base_dir, "data", "renners_stats.csv")

    if not os.path.exists(prijzen_file):
        st.error(f"🚨 Het bestand `{prijzen_file}` ontbreekt in je map!")
        return pd.DataFrame()
    if not os.path.exists(stats_file):
        st.error(f"🚨 Het bestand `{stats_file}` ontbreekt in je map!")
        return pd.DataFrame()

    try:
        df_prog  = pd.read_csv(prijzen_file, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
        df_stats = pd.read_csv(stats_file,   sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')

        df_prog.columns  = df_prog.columns.str.strip()
        df_stats.columns = df_stats.columns.str.strip()

        if 'Naam' in df_prog.columns:  df_prog  = df_prog.rename(columns={'Naam': 'Renner'})
        if 'Naam' in df_stats.columns: df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        if 'Ploeg' in df_stats.columns: df_stats = df_stats.rename(columns={'Ploeg': 'Team'})

        df_stats = df_stats.drop_duplicates(subset=['Renner'], keep='first')
        norm_to_stats = {normalize_name_logic(n): n for n in df_stats['Renner'].unique()}
        df_prog['Renner_Stats'] = df_prog['Renner'].apply(lambda x: match_naam_slim(x, norm_to_stats))

        merged_df = pd.merge(
            df_prog, df_stats,
            left_on='Renner_Stats', right_on='Renner',
            how='left', suffixes=('', '_drop')
        )
        merged_df = merged_df.drop(columns=[c for c in merged_df.columns if '_drop' in c or c == 'Renner_Stats'])

        if 'Prijs' not in merged_df.columns:
            st.error("🚨 Fout in de startlijst: de kolom `Prijs` is niet gevonden.")
            return pd.DataFrame()

        merged_df['Prijs'] = pd.to_numeric(merged_df['Prijs'], errors='coerce').fillna(0.0).astype(float)
        merged_df.loc[merged_df['Prijs'] > 1000, 'Prijs'] = merged_df['Prijs'] / 1000000
        merged_df.loc[merged_df['Prijs'] == 0.8, 'Prijs'] = 0.75

        merged_df = (
            merged_df[merged_df['Prijs'] > 0]
            .sort_values(by='Prijs', ascending=False)
            .drop_duplicates(subset=['Renner'])
        )

        if merged_df.empty:
            st.error("🚨 De bestanden zijn geladen, maar na filtering (Prijs > 0) bleven er 0 renners over.")
            return pd.DataFrame()

        for col in ['GC', 'SPR', 'ITT', 'MTN']:
            if col not in merged_df.columns: merged_df[col] = 0
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0).astype(int)

        # Standardize "Naam" / "Renner" handling so both modules work properly
        # Sporza_Giro_Bouwer traditionally used 'Naam'. We'll provide both.
        if 'Naam' not in merged_df.columns:
            merged_df['Naam'] = merged_df['Renner']

        return merged_df
    except Exception as e:
        st.error(f"🚨 Er trad een fout op bij het laden van de data: {e}")
        return pd.DataFrame()

def calculate_giro_ev(df):
    df = df.copy()
    df['EV_GC']  = (df['GC']  / 100)**4 * 400
    df['EV_SPR'] = (df['SPR'] / 100)**4 * 250
    df['EV_ITT'] = (df['ITT'] / 100)**4 * 80
    df['EV_MTN'] = (df['MTN'] / 100)**4 * 100
    df['Giro_EV'] = (df['EV_GC'] + df['EV_SPR'] + df['EV_ITT'] + df['EV_MTN']).fillna(0).round(0).astype(int)

    # Backwards compatibility for Sporza_Giro_Bouwer
    df['EV'] = df['Giro_EV']

    df['Waarde (EV/M)'] = (df['Giro_EV'] / df['Prijs']).replace([float('inf'), -float('inf')], 0).fillna(0).round(1)

    def bepaal_rol(row):
        if row['GC']  >= 85: return 'Klassementsrenner'
        if row['SPR'] >= 85: return 'Sprinter'
        if row['ITT'] >= 85 and row['GC'] < 75: return 'Tijdrijder'
        if row['MTN'] >= 80 and row['GC'] < 80: return 'Aanvaller / Klimmer'
        return 'Knecht / Vrijbuiter'

    df['Type'] = df.apply(bepaal_rol, axis=1)
    return df
