@st.cache_data
def load_data():
    try:
        df_p = pd.read_csv("renners_prijzen.csv")
        df_wo = pd.read_csv("renners_stats.csv")
        df_sl = pd.read_csv("startlijsten.csv")
        
        df_p['Match_Name'] = df_p['Naam'].str.lower().str.strip()
        
        def convert_to_short_name(full_name):
            parts = str(full_name).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}".lower()
            return str(full_name).lower()
        
        df_wo['Match_Name'] = df_wo['Naam'].apply(convert_to_short_name)
        df_sl['Match_Name'] = df_sl['Naam'].str.lower().str.strip()
        
        df = pd.merge(df_p, df_wo, on='Match_Name', how='inner', suffixes=('', '_wo'))
        df = pd.merge(df, df_sl.drop(columns=['Naam']), on='Match_Name', how='left')
        
        # Zet de cijfers om naar vinkjes voor de weergave
        races = ["OHN","KBK","SB","PN7","TA7","MSR","BDP","E3","GW","DDV","RVV","SP","PR","BP","AGR","WP","LBL"]
        for r in races:
            df[r] = df[r].apply(lambda x: "✅" if x == 1 else "❌")
            
        df['Prijs_Clean'] = pd.to_numeric(df['Prijs'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Fout bij laden bestanden: {e}")
        return pd.DataFrame()
