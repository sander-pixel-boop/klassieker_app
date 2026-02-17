import streamlit as st
import pandas as pd
import pulp
import io

st.set_page_config(page_title="Scorito Master 2026", layout="wide", page_icon="🚴")

# --- 1. DATA INLADEN ---
@st.cache_data
def load_data():
    try:
        # Laden van de drie CSV bestanden van GitHub
        df_p = pd.read_csv("renners_prijzen.csv")
        df_wo = pd.read_csv("renners_stats.csv")
        df_sl = pd.read_csv("startlijsten.csv")
        
        # Namen normaliseren voor matching
        df_p['Match_Name'] = df_p['Naam'].str.lower().str.strip()
        
        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                # Tadej Pogačar -> t. pogačar
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower()
            return str(full_name).lower()
        
        df_wo['Match_Name'] = df_wo['Naam'].apply(convert_to_short_name)
        df_sl['Match_Name'] = df_sl['Naam'].str.lower().str.strip()
        
        # Stap 1: Prijzen koppelen aan WielerOrakel stats
        df = pd.merge(df_p, df_wo, on='Match_Name', how='inner', suffixes=('', '_wo'))
        
        # Stap 2: Startlijst informatie toevoegen
        df = pd.merge(df, df_sl.drop(columns=['Naam']), on='Match_Name', how='left')
        
        # Prijs opschonen naar getal
        df['Prijs_Clean'] = pd.to_numeric(df['Prijs'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        # NaN waarden in startlijsten vullen met 0
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        for r in races:
            df[r] = df[r].fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Fout bij laden van bestanden: {e}")
        return pd.DataFrame()

df = load_data()

# --- 2. CUSTOM CSS VOOR GEDRAAIDE HEADERS ---
st.markdown("""
    <style>
    /* Stijlen voor de wedstrijdtabel headers */
    .stDataFrame th div {
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .stDataFrame th {
        vertical-align: bottom !important;
        text-align: center !important;
    }
    /* De eigenlijke rotatie */
    [data-testid="stTable"] th, [data-testid="stDataFrame"] th {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. UI STRUCTUUR ---
st.title("🏆 Scorito Klassieker Master 2026")

if df.empty:
    st.error("Data kon niet worden geladen. Controleer of 'renners_prijzen.csv', 'renners_stats.csv' en 'startlijsten.csv' in je GitHub repo staan.")
else:
    tab1, tab2, tab3 = st.tabs(["🚀 Team Samensteller", "📅 Wedstrijdschema", "ℹ️ Informatie"])

    # --- SIDEBAR: STRATEGIE ---
    with st.sidebar:
        st.header("⚙️ Instellingen")
        budget = st.number_input("Totaal Budget (€)", value=46000000, step=500000)
        
        st.divider()
        st.subheader("🎯 Strategie Gewicht")
        
        w_cob = st.slider("Kassei (COB)", 0, 10, 8, help="Belangrijk voor: OHN, KBK, E3, GW, DDV, RVV, PR")
        st.caption("Omloop, Kuurne, E3, Gent-W, Dwars door Vl, Vlaanderen, Roubaix")
        
        w_hll = st.slider("Heuvel (HLL)", 0, 10, 6, help="Belangrijk voor: MSR, BP, AGR, WP, LBL")
        st.caption("Sanremo, Brabantse, Amstel, Waalse Pijl, Luik")
        
        w_mtn = st.slider("Klim (MTN)", 0, 10, 4, help="Cruciaal voor de nieuwe Parijs-Nice Etappe 7!")
        st.caption("Parijs-Nice Etappe 7 (Klimrit)")
        
        w_spr = st.slider("Sprint (SPR)", 0, 10, 5, help="Belangrijk voor: KBK, MSR, BDP, GW, SP, TA Etappe 7")
        st.caption("Kuurne, Sanremo, De Panne, Gent-W, Scheldeprijs, Tirreno Et. 7")
        
        w_or  = st.slider("Eendags kwaliteit (OR)", 0, 10, 5, help="Algemene score van WielerOrakel voor eendagswedstrijden.")
        
        st.divider()
        if st.button("🔄 Herlaad Data"):
            st.cache_data.clear()
            st.rerun()

    # Score berekenen op basis van sliders
    df['Score'] = (df['COB'] * w_cob) + (df['HLL'] * w_hll) + (df['MTN'] * w_mtn) + (df['SPR'] * w_spr) + (df['OR'] * w_or)

    # --- TAB 1: SAMENSTELLER ---
    with tab1:
        col_list, col_team = st.columns([1, 1])
        
        with col_list:
            st.subheader("📊 Toprenners voor jouw strategie")
            st.dataframe(
                df[['Naam', 'Prijs_Clean', 'Score']].sort_values('Score', ascending=False).head(25),
                column_config={"Prijs_Clean": st.column_config.NumberColumn("Prijs", format="€ %d")}
            )

        with col_team:
            st.subheader("🚀 Optimalisatie")
            if st.button("Genereer Optimaal Team (20 renners)"):
                prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
                sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
                
                # Doel: Maximaliseer de berekende score
                prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
                # Beperkingen: Budget en aantal renners
                prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
                prob += pulp.lpSum([sel[i] for i in df.index]) == 20
                
                prob.solve()
                
                if pulp.LpStatus[prob.status] == 'Optimal':
                    st.session_state['selected_team_idx'] = [i for i in df.index if sel[i].varValue == 1]
                    st.success(f"Team gevonden! Kosten: € {df.loc[st.session_state['selected_team_idx'], 'Prijs_Clean'].sum():,.0f}")
                else:
                    st.error("Geen oplossing mogelijk binnen budget.")

            if 'selected_team_idx' in st.session_state:
                team = df.loc[st.session_state['selected_team_idx']]
                st.dataframe(
                    team[['Naam', 'Prijs_Clean', 'COB', 'HLL', 'SPR']].sort_values('Prijs_Clean', ascending=False),
                    column_config={"Prijs_Clean": st.column_config.NumberColumn("Prijs", format="€ %d")}
                )
            else:
                st.info("Klik op de knop om een team te genereren.")

    # --- TAB 2: WEDSTRIJDSCHEMA ---
    with tab_programma:
        if 'selected_team_idx' not in st.session_state:
            st.info("Genereer eerst een team in het tabblad 'Team Samensteller'.")
        else:
            team_schema = df.loc[st.session_state['selected_team_idx']].copy()
            races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
            
            # Zet de 1/0 om naar leesbare vinkjes
            for r in races:
                team_schema[r] = team_schema[r].apply(lambda x: "✅" if x == 1 else "")
            
            st.subheader("Gedetailleerd Wedstrijdschema")
            st.write("Vinkjes zijn gebaseerd op de startlijsten in 'startlijsten.csv'.")
            st.dataframe(team_schema[['Naam'] + races], height=700)
            
            # Statistiek onderaan
            summary = {r: (team_schema[r] == "✅").sum() for r in races}
            st.subheader("Aantal renners per koers")
            st.bar_chart(pd.Series(summary))

    # --- TAB 3: INFORMATIE ---
    with tab_info:
        st.header("ℹ️ Over deze applicatie")
        st.write("""
        Deze tool helpt bij het samenstellen van het optimale Scorito Klassiekerspel-team door gebruik te maken van wiskundige optimalisatie (Linear Programming).
        """)
        
        st.subheader("Bronnen & Credits")
        st.markdown("""
        De data in deze app wordt mogelijk gemaakt door:
        
        * **[WielerOrakel.nl](https://www.cyclingoracle.com/):** Alle kwaliteitsratings (COB, HLL, SPR, etc.) zijn gebaseerd op hun geavanceerde modellen. Een enorme shout-out naar het team van WielerOrakel!
        * **[ProCyclingStats (PCS)](https://www.procyclingstats.com/):** De startlijsten worden gecontroleerd via PCS om te zien wie er daadwerkelijk aan de start staan.
        * **[Scorito.com](https://www.scorito.com/):** De basis voor de prijzen en de puntentelling van het spel.
        """)
        
        st.subheader("Uitleg Ratings")
        st.markdown("""
        * **COB (Cobbles):** Kwaliteit op kasseien (bijv. Ronde van Vlaanderen).
        * **HLL (Hills):** Kwaliteit in de heuvels (bijv. Luik-Bastenaken-Luik).
        * **MTN (Mountain):** Belangrijk voor de nieuwe **Parijs-Nice Etappe 7**.
        * **SPR (Sprint):** Voor massasprints en finales in **Tirreno Etappe 7**.
        * **OR (One Day Race):** Algemene score voor eendagswedstrijden.
        """)
        
        st.divider()
        st.write("De afkortingen in het schema:")
        r_info = {
            "OHN": "Omloop Het Nieuwsblad", "KBK": "Kuurne-Brussel-Kuurne", "SB": "Strade Bianche",
            "PN7": "Parijs-Nice Etappe 7 (Klim)", "TA7": "Tirreno-Adriatico Etappe 7 (Sprint)",
            "MSR": "Milano-Sanremo", "BDP": "Brugge-De Panne", "E3": "E3 Saxo Classic",
            "GW": "Gent-Wevelgem", "DDV": "Dwars door Vlaanderen", "RVV": "Ronde van Vlaanderen",
            "SP": "Scheldeprijs", "PR": "Parijs-Roubaix", "BP": "Brabantse Pijl",
            "AGR": "Amstel Gold Race", "WP": "Waalse Pijl", "LBL": "Luik-Bastenaken-Luik"
        }
        cols = st.columns(2)
        for i, (k, v) in enumerate(r_info.items()):
            with cols[i % 2]:
                st.write(f"**{k}**: {v}")
