import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

st.set_page_config(page_title="PCS Startlijst Updater")

st.title("🔄 PCS Startlijst Updater")
st.write("Klik op de knop hieronder om de nieuwste startlijsten van ProCyclingStats op te halen.")

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

def get_riders(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        return [a.text.strip().lower() for a in soup.find_all('a', href=True) if 'rider/' in a['href']]
    except:
        return []

if st.button("Start Scraping (duurt ca. 20 seconden)"):
    # Probeer rennerslijst te laden voor de basis
    try:
        base_df = pd.read_csv("renners_prijzen.csv", sep=None, engine='python')
        all_names = base_df.iloc[:, 0].tolist()
    except:
        all_names = []
        st.error("renners_prijzen.csv niet gevonden. Upload die eerst.")

    if all_names:
        results = {}
        progress = st.progress(0)
        
        for i, (abbr, url) in enumerate(RACES.items()):
            st.write(f"Ophalen: {abbr}...")
            results[abbr] = get_riders(url)
            progress.progress((i + 1) / len(RACES))
            time.sleep(0.5)

        # Bouw de matrix
        final_data = []
        for name in all_names:
            row = {"Naam": name}
            # Pak de achternaam voor de check
            last_name = name.lower().split()[-1]
            for abbr in RACES.keys():
                row[abbr] = 1 if any(last_name in r for r in results[abbr]) else 0
            final_data.append(row)

        df_out = pd.DataFrame(final_data)
        
        st.success("Klaar! Download de CSV en vervang 'startlijsten.csv' in je GitHub.")
        csv = df_out.to_csv(index=False).encode('utf-8')
        st.download_button("Download startlijsten.csv", csv, "startlijsten.csv", "text/csv")
