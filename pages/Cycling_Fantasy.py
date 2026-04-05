import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
from thefuzz import process, fuzz
import io
import re
from pypdf import PdfReader
import os

# --- CONFIGURATIE ---
st.set_page_config(page_title="Cycling Fantasy AI", layout="wide", page_icon="🚲")

# --- PADEN NAAR BRONBESTANDEN (IN MAIN) ---
STATS_PATH = "renners_stats.csv"
PRICES_PATH = "cf_prijzen.csv"

# --- STATISCHE DATA LADEN (STATS + PRIJZEN) ---
@st.cache_data
def load_static_data() -> pd.DataFrame:
    """
    Loads static rider stats and prices from CSV files,
    cleans the data, and merges them using fuzzy matching.

    Returns:
        pd.DataFrame: A DataFrame containing rider names, stats, and prices.
    """
    try:
        # 1. Stats laden uit de root
        if not os.path.exists(STATS_PATH):
            st.error(f"Bestand '{STATS_PATH}' niet gevonden in de root map.")
            return pd.DataFrame()
            
        df_stats = pd.read_csv(STATS_PATH, sep='\t') 
        if 'Naam' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Naam': 'Renner'})
        if 'Team' not in df_stats.columns and 'Ploeg' in df_stats.columns:
            df_stats = df_stats.rename(columns={'Ploeg': 'Team'})
            
        df_stats = df_stats.drop_duplicates(subset=['Renner'], keep='first')

        all_stats_cols = ['COB', 'HLL', 'SPR', 'AVG', 'FLT', 'MTN', 'ITT', 'GC', 'OR', 'TTL']
        for col in all_stats_cols:
            if col not in df_stats.columns:
                df_stats[col] = 0
            df_stats[col] = pd.to_numeric(df_stats[col], errors='coerce').fillna(0).astype(int)

        if 'Team' not in df_stats.columns:
            df_stats['Team'] = 'Onbekend'
        else:
            df_stats['Team'] = df_stats['Team'].fillna('Onbekend')

        # 2. Prijzen laden uit de root
        try:
            if os.path.exists(PRICES_PATH):
                df_prices = pd.read_csv(PRICES_PATH, sep=None, engine='python')
                if 'Naam' in df_prices.columns:
                    df_prices = df_prices.rename(columns={'Naam': 'Renner'})
            else:
                st.warning(f"⚠️ Bestand '{PRICES_PATH}' niet gevonden in root. Alle renners krijgen 200 credits.")
                df_prices = pd.DataFrame(columns=['Renner', 'Prijs'])
        except Exception:
            df_prices = pd.DataFrame(columns=['Renner', 'Prijs'])

        # Koppel prijzen aan de stats via Fuzzy Match
        full_names = df_stats['Renner'].tolist()
        
        if not df_prices.empty:
            # We doen een kleine pre-match om de merge sneller te maken
            price_map = {}
            for _, row in df_prices.iterrows():
                match = process.extractOne(str(row['Renner']), full_names, scorer=fuzz.token_set_ratio)
                if match and match[1] > 85:
                    price_map[match[0]] = row['Prijs']
            
            df_stats['Prijs'] = df_stats['Renner'].map(price_map)
        else:
            df_stats['Prijs'] = 200

        # CF Regel: Niet in de lijst = 200 credits
        df_stats['Prijs'] = df_stats['Prijs'].fillna(200).astype(int)
        return df_stats
        
    except Exception as e:
        st.error(f"Fout bij laden statische data: {e}")
        return pd.DataFrame()

# --- PDF PARSER VOOR PCS STARTLIJSTEN ---
def parse_pcs_pdf(uploaded_file) -> pd.DataFrame:
    """
    Parses a PDF file from ProCyclingStats to extract a list of rider names.

    Args:
        uploaded_file: The uploaded PDF file object.

    Returns:
        pd.DataFrame: A DataFrame containing the extracted rider names under the 'Renner' column.
    """
    try:
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        raw_chunks = re.split(r'  +|\n', text)
        potential_names = []
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk: continue
            
            # Zoek naar patronen zoals "1. Tadej Pogacar" of "121 Philipsen Jasper"
            match = re.search(r'^\d{1,3}\.?\s+([A-Za-zÀ-ÖØ-öø-ÿ\-\'\s]{4,})', chunk)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\s+\d+$', '', name).strip() # Verwijder leeftijd-getallen aan eind
                potential_names.append(name)
            elif len(chunk) > 5 and not any(char.isdigit() for char in chunk):
                potential_names.append(chunk)

        return pd.DataFrame({'Renner': potential_names})
    except Exception as e:
        st.error(f"Fout bij lezen PDF: {e}")
        return pd.DataFrame()

# --- STARTLIJST VERWERKEN ---
def process_startlist(uploaded_file, df_static: pd.DataFrame) -> pd.DataFrame:
    """
    Processes an uploaded startlist file (PDF, CSV, or Excel) and matches the names
    against the static rider database.

    Args:
        uploaded_file: The uploaded file object.
        df_static (pd.DataFrame): The static rider database.

    Returns:
        pd.DataFrame: A DataFrame containing the matched riders from the startlist.
    """
    try:
        if uploaded_file.name.lower().endswith('.pdf'):
            df_start = parse_pcs_pdf(uploaded_file)
        elif uploaded_file.name.lower().endswith('.csv'):
            df_start = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df_start = pd.read_excel(uploaded_file)
            
        if not uploaded_file.name.lower().endswith('.pdf'):
            col_name = next((c for c in ['Renner', 'Rider', 'Naam', 'Name'] if c in df_start.columns), df_start.columns[0])
            df_start = df_start.rename(columns={col_name: 'Renner'})
        
        full_names = df_static['Renner'].tolist()
        
        def match_name_upload(name: str):
            if not name or pd.isna(name): return None
            match = process.extractOne(str(name), full_names, scorer=fuzz.token_set_ratio)
            return match[0] if match and match[1] > 75 else None
            
        df_start['Renner_Matched'] = df_start['Renner'].apply(match_name_upload)
        df_start = df_start.dropna(subset=['Renner_Matched'])
        
        df_race = pd.merge(df_start[['Renner_Matched']], df_static, left_on='Renner_Matched', right_on='Renner', how='inner')
        return df_race.drop_duplicates(subset=['Renner'])
    except Exception as e:
        st.error(f"Fout bij verwerken startlijst: {e}")
        return pd.DataFrame()

# --- CF EV CALCULATOR ---
def calculate_cf_ev(df: pd.DataFrame, stat: str, method: str) -> pd.DataFrame:
    """
    Calculates the Expected Value (EV) for each rider based on the chosen statistic and method.

    Args:
        df (pd.DataFrame): The dataframe containing the riders.
        stat (str): The column name of the statistic to use for evaluation.
        method (str): The method to calculate EV ('Ranking (CF Punten)' or 'Macht 4 Curve').

    Returns:
        pd.DataFrame: The dataframe with added 'CF_EV' and 'Waarde (EV/Credit)' columns.
    """
    df = df.copy()
    df = df.sort_values(by=[stat, 'AVG'], ascending=[False, False]).reset_index(drop=True)
    cf_pts = [45, 25, 22, 19, 17, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    
    if "Ranking (CF Punten)" in method:
        # Vectorized assignment for ranking method
        cf_ev_values = cf_pts + [0.0] * max(0, len(df) - len(cf_pts))
        df['CF_EV'] = pd.Series(cf_ev_values[:len(df)], dtype=float)
    else:
        # Vectorized power of 4 curve
        df['CF_EV'] = (df[stat] / 100)**4 * 45
        
    df['Waarde (EV/Credit)'] = (df['CF_EV'] / df['Prijs']).replace([float('inf'), -float('inf')], 0).fillna(0).round(4)
    return df

# --- SOLVER ---
def solve_cf_team(dataframe: pd.DataFrame, total_budget: int, force_list: list, exclude_list: list) -> list:
    """
    Solves the Knapsack problem to find the optimal team of 9 riders within the budget constraints.

    Args:
        dataframe (pd.DataFrame): The dataframe containing riders with their EV and prices.
        total_budget (int): The maximum budget available for the team.
        force_list (list): A list of rider names that must be included in the team.
        exclude_list (list): A list of rider names that must be excluded from the team.

    Returns:
        list: A list of the optimal 9 rider names, or None if no optimal solution is found.
    """
    prob = pulp.LpProblem("CF_Solver", pulp.LpMaximize)
    rider_vars = pulp.LpVariable.dicts("Riders", dataframe.index, cat='Binary')
    
    prob += pulp.lpSum([dataframe.loc[i, 'CF_EV'] * rider_vars[i] for i in dataframe.index])
    prob += pulp.lpSum([rider_vars[i] for i in dataframe.index]) == 9
    prob += pulp.lpSum([dataframe.loc[i, 'Prijs'] * rider_vars[i] for i in dataframe.index]) <= total_budget
    
    for i in dataframe.index:
        renner = dataframe.loc[i, 'Renner']
        if renner in force_list: prob += rider_vars[i] == 1
        if renner in exclude_list: prob += rider_vars[i] == 0
            
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))
    if pulp.LpStatus[prob.status] == 'Optimal':
        return [dataframe.loc[i, 'Renner'] for i in dataframe.index if rider_vars[i].varValue > 0.5]
    return []

# --- HOOFDCODE ---
df_static = load_static_data()
if df_static.empty:
    st.warning("De database kon niet worden geïnitialiseerd. Controleer of de CSV bestanden in de root map staan.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🚲 CF AI Coach")
    st.header("📂 1. Upload Startlijst")
    uploaded_file = st.file_uploader("Upload PCS PDF, CSV of Excel", type=['pdf', 'csv', 'xlsx', 'xls'], help="Upload de startlijst van de koers in PDF, CSV, of Excel formaat.")
    
    st.header("⚙️ 2. Instellingen")
    stat_mapping = {
        'Kasseien (COB)': 'COB', 
        'Heuvels (HLL)': 'HLL', 
        'Sprint (SPR)': 'SPR', 
        'Allround (AVG)': 'AVG', 
        'Klimmen (MTN)': 'MTN', 
        'Tijdrit (ITT)': 'ITT'
    }
    koers_type = st.selectbox("🏁 Type Koers:", list(stat_mapping.keys()), help="Selecteer het type koers om de bijbehorende statistieken te gebruiken.")
    ev_method = st.selectbox("🧮 Rekenmodel", ["1. Ranking (CF Punten)", "2. Macht 4 Curve"], help="Kies de berekeningsmethode voor de verwachte waarde (EV).")
    max_bud = st.number_input("💰 Budget (Credits)", value=5000, step=200, help="Vul het beschikbare budget in credits in.")
    
    df_race = pd.DataFrame()
    if uploaded_file:
        raw_race = process_startlist(uploaded_file, df_static)
        if not raw_race.empty:
            df_race = calculate_cf_ev(raw_race, stat_mapping[koers_type], ev_method)
            st.divider()
            with st.expander("🔒 Forceer / Uitsluit"):
                force_list = st.multiselect("🟢 Moet in team:", options=df_race['Renner'].tolist(), help="Kies renners die verplicht in je team moeten.")
                exclude_list = st.multiselect("🚫 Negeren:", options=[r for r in df_race['Renner'].tolist() if r not in force_list], help="Kies renners die niet in je team mogen.")
            
            if st.button("🚀 BEREKEN TEAM", type="primary", use_container_width=True, help="Klik om het optimale team te berekenen."):
                with st.spinner("Team berekenen... Dit kan even duren."):
                    st.session_state.cf_team = solve_cf_team(df_race, max_bud, force_list, exclude_list)

st.title("🚲 Cycling Fantasy Optimizer")
tab1, tab2, tab3 = st.tabs(["🚀 Optimaal Team", "📋 Database", "📖 Uitleg"])

with tab1:
    if uploaded_file is None:
        st.info("👈 Upload eerst de PDF startlijst van ProCyclingStats in de zijbalk.")
    elif "cf_team" in st.session_state and st.session_state.cf_team:
        team_df = df_race[df_race['Renner'].isin(st.session_state.cf_team)].sort_values(by='CF_EV', ascending=False).reset_index(drop=True)
        multipliers = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
        team_df['Tie-Breaker'] = [f"#{i+1} (x{m})" for i, m in enumerate(multipliers)]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Budget", f"{team_df['Prijs'].sum():.0f} / {max_bud}")
        m2.metric("🚴 Renners", f"{len(team_df)} / 9")
        m3.metric("🎯 Team EV", f"{team_df['CF_EV'].sum():.1f}")
        
        st.success("💡 **Tie-Breaker:** Gebruik de volgorde hieronder exact zo in de Cycling Fantasy app!")
        st.dataframe(team_df[['Tie-Breaker', 'Renner', 'Team', 'Prijs', 'CF_EV', stat_mapping[koers_type]]], hide_index=True, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(team_df, values='Prijs', names='Team', title="Team Budgetverdeling"), use_container_width=True)
        with c2:
            st.plotly_chart(px.bar(team_df, x='Renner', y='CF_EV', title="Verwachte Punten per Renner"), use_container_width=True)
    elif not df_race.empty:
        st.info("✅ Startlijst geladen. Klik op 'Bereken Team' in de zijbalk.")

with tab2:
    if not df_race.empty:
        st.subheader("Volledige Startlijst Analyse")
        st.dataframe(df_race[['Renner', 'Team', 'Prijs', 'CF_EV', 'Waarde (EV/Credit)', stat_mapping[koers_type]]].sort_values(by='CF_EV', ascending=False), hide_index=True, use_container_width=True)

with tab3:
    st.header("📖 Hoe werkt het?")
    st.markdown("""
    1. **PDF Import:** De app leest de officiële PDF startlijst van ProCyclingStats. Hij herkent rugnummers en namen.
    2. **Prijzen:** Hij koppelt namen aan `cf_prijzen.csv`. Renners buiten de top 200 kosten automatisch **200 credits**.
    3. **Tie-Breaker:** In Cycling Fantasy is de volgorde van je 9 renners de tie-breaker (multiplier x1.0 tot x0.2). De AI zet de renners met de hoogste puntenverwachting altijd bovenaan.
    4. **Requirements:** Zorg dat `pypdf` in je `requirements.txt` staat op GitHub.
    """)