import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

st.title("🏆 PCS Master Namen Generator")

YEAR = "2026"
RACES = {
    "OHN": f"https://www.procyclingstats.com/race/omloop-het-nieuwsblad/{YEAR}/startlist",
    "KBK": f"https://www.procyclingstats.com/race/kuurne-brussel-kuurne/{YEAR}/startlist",
    "SB":  f"https://www.procyclingstats.com/race/strade-bianche/{YEAR}/startlist",
    "PN7": f"https://www.procyclingstats.com/race/paris-nice/{YEAR}/startlist",
    "TA7": f"https://www.procyclingstats.com/race/tirreno-adriatico/{YEAR}/startlist",
    "MSR": f"https://www.procyclingstats.com/race/milano-sanremo/{YEAR}/startlist",
    "BDP": f"https://www.procyclingstats.com/race/classic-brugge-de-panne/{YEAR}/startlist",
    "E3":  f"https://www.procyclingstats.com/race/e3-harelbeke/{YEAR}/startlist",
    "GW":  f"https://www.procyclingstats.com/race/gent-wevelgem/{YEAR}/startlist",
    "DDV": f"https://www.procyclingstats.com/race/dwars-door-vlaanderen/{YEAR}/startlist",
    "RVV": f"https://www.procyclingstats.com/race/ronde-van-vlaanderen/{YEAR}/startlist",
    "SP":  f"https://www.procyclingstats.com/race/scheldeprijs/{YEAR}/startlist",
    "PR":  f"https://www.procyclingstats.com/race/paris-roubaix/{YEAR}/startlist",
    "BP":  f"https://www.procyclingstats.com/race/brabantse-pijl/{YEAR}/startlist",
    "AGR": f"https://www.procyclingstats.com/race/amstel-gold-race/{YEAR}/startlist",
    "WP":  f"https://www.procyclingstats.com/race/fleche-wallonne/{YEAR}/startlist",
    "LBL": f"https://www.procyclingstats.com/race/liege-bastogne-liege/{YEAR}/startlist"
}

if st.button("🚀 Haal ALLE PCS namen op"):
    all_pcs_riders = set()
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for abbr, url in RACES.items():
        st.write(f"Scannen: {abbr}...")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            # Pak alle namen uit de startlijst tabel
            for a in soup.find_all('a', href=True):
                if 'rider/' in a['href'] and len(a.text.strip()) > 3:
                    all_pcs_riders.add(a.text.strip())
            time.sleep(0.5)
        except:
            st.error(f"Fout bij {abbr}")

    df_master = pd.DataFrame(sorted(list(all_pcs_riders)), columns=["Naam"])
    st.success(f"Totaal {len(df_master)} unieke renners gevonden op PCS.")
    st.dataframe(df_master)
    
    csv = df_master.to_csv(index=False).encode('utf-8')
    st.download_button("Download Master Namenlijst", csv, "pcs_namen.csv", "text/csv")
