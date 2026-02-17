import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

st.set_page_config(page_title="PCS Master List Generator", layout="wide")

st.title("🏆 PCS Master Namen Generator")
st.write("Als de lijst leeg blijft, blokkeert PCS de server. Gebruik dan de knoppen per koers.")

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

if 'master_list' not in st.session_state:
    st.session_state['master_list'] = set()

def scrape_race(abbr, url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0 Safari/537.36'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            found = 0
            for a in soup.find_all('a', href=True):
                if 'rider/' in a['href'] and len(a.text.strip()) > 3:
                    st.session_state['master_list'].add(a.text.strip())
                    found += 1
            return found
        else:
            return f"Error {resp.status_code}"
    except Exception as e:
        return str(e)

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Start Alles (met pauzes)"):
        for abbr, url in RACES.items():
            res = scrape_race(abbr, url)
            st.write(f"{abbr}: {res} renners gevonden.")
            time.sleep(2) # Wacht 2 seconden tussen koersen
        st.success("Klaar!")

with col2:
    if st.button("🗑️ Wis lijst"):
        st.session_state['master_list'] = set()
        st.rerun()

st.divider()

# Laat de verzamelde lijst zien
master_df = pd.DataFrame(sorted(list(st.session_state['master_list'])), columns=["Naam"])
st.subheader(f"Verzamelde Namen ({len(master_df)})")
st.dataframe(master_df, use_container_width=True)

if not master_df.empty:
    csv = master_df.to_csv(index=False).encode('utf-8')
    st.download_button("📩 Download pcs_namen.csv", csv, "pcs_namen.csv", "text/csv")
