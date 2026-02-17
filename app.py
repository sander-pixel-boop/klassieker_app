import streamlit as st
import pandas as pd
import pulp
import io
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Scorito Manager: WielerOrakel Editie", layout="wide", page_icon="🚴")

# --- 1. CONFIGURATIE ---
YEAR = "2026"
RACES_URLS = {
    "Omloop": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist",
    "Kuurne": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist",
    "Strade": f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist",
    "PN Et.7": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist",
    "TA Et.7": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist",
    "MSR": f"https://www.procyclingstats.com/race/milano-sanremo/{YEAR}/startlist",
    "E3": f"https://www.procyclingstats.com/race/e3-harelbeke/{YEAR}/startlist",
    "Gent-W": f"https://www.procyclingstats.com/race/gent-wevelgem/{YEAR}/startlist",
    "DDV": f"https://www.procyclingstats.com/race/dwars-door-vlaanderen/{YEAR}/startlist",
    "RvV": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist",
    "Schelde": f"https://www.procyclingstats.com/race/scheldeprijs/{YEAR}/startlist",
    "Roubaix": f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist",
    "Brabantse": f"https://www.procyclingstats.com/race/brabantse-pijl/{YEAR}/startlist",
    "Amstel": f"https://www.procyclingstats.com/race/amstel-gold-race/{YEAR}/startlist",
    "Waalse Pijl": f"https://www.procyclingstats.com/race/fleche-wallonne/{YEAR}/startlist",
    "LBL": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist",
    "Eschborn": f"https://www.procyclingstats.com/race/eschborn-frankfurt/{YEAR}/startlist"
}

# --- 2. FUNCTIES ---

@st.cache_data(ttl=3600)
def scrape_pcs():
    startlists = {}
    # Placeholder voor progressie
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()
    total = len(RACES_URLS)
    count = 0
    
    for race_name, url in RACES_URLS.items():
        status_text.text(f"Ophalen: {race_name}...")
        riders_in_race = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                rider_links = soup.select('a[href^="rider/"]')
                for link in rider_links:
                    riders_in_race.append(link.text.strip().lower())
        except:
            pass
        startlists[race_name] = riders_in_race
        count += 1
        progress_bar.progress(count / total)
        time.sleep(0.1)
        
    status_text.text("✅ Startlijsten binnen!")
    progress_bar.empty()
    return startlists

def convert_wo_name_to_scorito(full_name):
    # Converteert "Tadej Pogačar" naar "t. pogačar" voor matching
    parts = str(full_name).split()
    if len(parts) >= 2:
        # Pak eerste letter van voornaam + punt + rest van naam
        short_name = f"{parts[0][0]}. {' '.join(parts[1:])}"
        return short_name.lower()
    return str(full_name).lower()

def load_wielerorakel_data(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file, sep=None, engine='python')
    else:
        df = pd.read_excel(file)
    
    # Kolommen normaliseren
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Mapping
    rename_dict = {
        'COB': 'Kassei',
        'HLL': 'Heuvel',
        'SPR': 'Sprint',
        'MTN': 'Klim', # Belangrijk voor PN!
        'OR': 'Eendags', # Belangrijk voor klassiekers!
        'NAAM': 'Naam_Stats'
    }
    
    # Hernoem kolommen die bestaan
    df.rename(columns={k: v for k, v in rename_dict.items() if k in df.columns}, inplace=True)
    
    # Maak match naam aan
    if 'Naam_Stats' in df.columns:
        df['Match_Name'] = df['Naam_Stats'].apply(convert_wo_name_to_scorito)
    
    # Vul lege waarden met 0
    cols_to_fill = ['Kassei', 'Heuvel', 'Sprint', 'Klim', 'Eendags']
    for c in cols_to_fill:
        if c in df.columns:
            df[c] = df[c].fillna(0)
    
    return df

# --- 3. UI & LOGICA ---

st.title("🏆 Scorito Manager: WielerOrakel Editie")

with st.sidebar:
    st.header("1. Data Invoer")
    
    # Uploads
    prices_file = st.file_uploader("Stap A: Upload Scorito Prijslijst (CSV)", type=["csv", "xlsx"])
    wo_file = st.file_uploader("Stap B: Upload WielerOrakel Bestand (CSV)", type=["csv", "xlsx"])
    
    st.divider()
    if st.button("🔄 Update Startlijsten (PCS)"):
        st.session_state['pcs_data'] = scrape_pcs()

# LOGICA
if prices_file and wo_file:
    # 1. Laad Prijzen
    if prices_file.name.endswith('.csv'):
        df_p = pd.read_csv(prices_file, sep=None, engine='python')
    else:
        df_p = pd.read_excel(prices_file)
        
    df_p['Prijs_Clean'] = pd.to_numeric(df_p['Prijs'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    df_p['Match_Name'] = df_p['Naam'].str.lower().str.strip()
    
    # 2. Laad WielerOrakel
    try:
        df_wo = load_wielerorakel_data(wo_file)
        st.success(f"✅ Data geladen! {len(df_wo)} renners uit WielerOrakel gevonden.")
    except Exception as e:
        st.error(f"Fout bij lezen WielerOrakel bestand: {e}")
        st.stop()

    # 3. Merge
    merged = pd.merge(df_p, df_wo, on='Match_Name', how='left', suffixes=('', '_stats'))
    
    # Check gemiste matches
    missing = merged[merged['Kassei'].isna()]
    if not missing.empty:
        with st.expander(f"⚠️ {len(missing)} renners uit je prijslijst hebben geen data gevonden"):
            st.dataframe(missing[['Naam', 'Prijs']])
            st.info("Tip: Namen moeten overeenkomen (bijv. 'T. Pogačar'). De app probeert dit automatisch, maar soms wijkt de spelling af.")

    # Filter voor berekening
    df_final = merged.dropna(subset=['Kassei']).copy()
    
    # 4. Startlijsten toevoegen
    if 'pcs_data' in st.session_state:
        for race, riders in st.session_state['pcs_data'].items():
            df_final[race] = df_final['Match_Name'].apply(lambda x: "✅" if any(x in r or r in x for r in riders) else "")

    # D. STRATEGIE DASHBOARD
    st.sidebar.header("2. Strategie")
    budget = st.sidebar.number_input("Budget (€)", value=46000000, step=250000)
    
    st.sidebar.subheader("Weging Kwaliteiten")
    w_kassei = st.sidebar.slider("Kassei (RvV/Roubaix)", 0, 10, 8)
    w_heuvel = st.sidebar.slider("Heuvel (LBL/Waalse Pijl)", 0, 10, 6)
    w_sprint = st.sidebar.slider("Sprint (Schelde/TA)", 0, 10, 4)
    w_klim   = st.sidebar.slider("Klim (PN Rit 7)", 0, 10, 5, help="Belangrijk voor Parijs-Nice etappe 7!")
    w_or     = st.sidebar.slider("Eendags (Algemeen)", 0, 10, 5, help="De 'OR' score van WielerOrakel. Goede graadmeter voor klassiekers.")
    
    # Score Formule (WielerOrakel is 0-100)
    df_final['Score'] = (
        (df_final['Kassei'] * w_kassei) + 
        (df_final['Heuvel'] * w_heuvel) + 
        (df_final['Sprint'] * w_sprint) + 
        (df_final['Klim'] * w_klim * 0.5) + # Klim telt deels
        (df_final['Eendags'] * w_or)
    )
    
    col1, col2 = st.columns([1,1])
    
    with col1:
        st.subheader("📊 Top Renners")
        # Kolommen kiezen om te tonen
        show_cols = ['Naam', 'Prijs_Clean', 'Score', 'Kassei', 'Heuvel', 'Sprint']
        if 'Eendags' in df_final.columns: show_cols.append('Eendags')
        
        st.dataframe(df_final[show_cols].sort_values('Score', ascending=False).head(15))
        
    with col2:
        st.subheader("🚀 Het Optimale Team")
        if st.button("Genereer Team"):
            prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
            sel = pulp.LpVariable.dicts("Sel", df_final.index, cat='Binary')
            
            prob += pulp.lpSum([df_final['Score'][i] * sel[i] for i in df_final.index])
            prob += pulp.lpSum([df_final['Prijs_Clean'][i] * sel[i] for i in df_final.index]) <= budget
            prob += pulp.lpSum([sel[i] for i in df_final.index]) == 20
            
            prob.solve()
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                team = df_final.loc[[i for i in df_final.index if sel[i].varValue == 1]]
                st.balloons()
                st.success(f"Team Kosten: € {team['Prijs_Clean'].sum():,.0f}")
                
                # Toon kolommen
                res_cols = ['Naam', 'Prijs', 'Eendags']
                if 'pcs_data' in st.session_state:
                    res_cols += ['PN Et.7', 'TA Et.7', 'RvV', 'LBL']
                
                st.dataframe(team[res_cols].sort_values('Prijs', ascending=False), height=600)
            else:
                st.error("Geen oplossing mogelijk binnen budget.")

elif not prices_file:
    st.info("👈 Upload eerst je Scorito Prijslijst.")
elif not wo_file:
    st.info("👈 Upload nu je WielerOrakel bestand.")
