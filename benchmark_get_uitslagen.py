import time
import pandas as pd
import os
from thefuzz import process, fuzz

def get_uitslagen_old(file_mod_time, alle_renners):
    if not os.path.exists("uitslagen.csv"):
        return pd.DataFrame()
    try:
        df_raw_uitslagen = pd.read_csv("uitslagen.csv", sep=None, engine='python')
        df_raw_uitslagen.columns = [str(c).strip().title() for c in df_raw_uitslagen.columns]

        if 'Race' not in df_raw_uitslagen.columns or 'Rider' not in df_raw_uitslagen.columns or 'Rnk' not in df_raw_uitslagen.columns:
            return pd.DataFrame()

        scorito_naar_sporza_map = {
            'OHN': 'OML', 'SB': 'STR', 'BDP': 'RVB',
            'GW': 'IFF', 'BP': 'BRP', 'AGR': 'AGT', 'WP': 'WAP'
        }

        uitslag_parsed = []
        for row in df_raw_uitslagen.itertuples():
            koers_origineel = str(row.Race).strip().upper()
            koers = scorito_naar_sporza_map.get(koers_origineel, koers_origineel)

            rank_str = str(row.Rnk).strip().upper()
            if rank_str in ['DNS', 'NAN', '']:
                continue

            rider_name = str(row.Rider).strip()
            match = process.extractOne(rider_name, alle_renners, scorer=fuzz.token_set_ratio)
            if match and match[1] > 70:
                uitslag_parsed.append({
                    "Race": koers,
                    "Rnk": rank_str,
                    "Renner": match[0]
                })
        return pd.DataFrame(uitslag_parsed)
    except:
        return pd.DataFrame()

def get_uitslagen_new(file_mod_time, alle_renners):
    if not os.path.exists("uitslagen.csv"):
        return pd.DataFrame()
    try:
        df_raw_uitslagen = pd.read_csv("uitslagen.csv", sep=None, engine='python')
        df_raw_uitslagen.columns = [str(c).strip().title() for c in df_raw_uitslagen.columns]

        if 'Race' not in df_raw_uitslagen.columns or 'Rider' not in df_raw_uitslagen.columns or 'Rnk' not in df_raw_uitslagen.columns:
            return pd.DataFrame()

        scorito_naar_sporza_map = {
            'OHN': 'OML', 'SB': 'STR', 'BDP': 'RVB',
            'GW': 'IFF', 'BP': 'BRP', 'AGR': 'AGT', 'WP': 'WAP'
        }

        uitslag_parsed = []
        match_cache = {}

        for race, rnk, rider in zip(df_raw_uitslagen['Race'], df_raw_uitslagen['Rnk'], df_raw_uitslagen['Rider']):
            koers_origineel = str(race).strip().upper()
            koers = scorito_naar_sporza_map.get(koers_origineel, koers_origineel)

            rank_str = str(rnk).strip().upper()
            if rank_str in ['DNS', 'NAN', '']:
                continue

            rider_name = str(rider).strip()
            if rider_name not in match_cache:
                match_cache[rider_name] = process.extractOne(rider_name, alle_renners, scorer=fuzz.token_set_ratio)

            match = match_cache[rider_name]

            if match and match[1] > 70:
                uitslag_parsed.append({
                    "Race": koers,
                    "Rnk": rank_str,
                    "Renner": match[0]
                })
        return pd.DataFrame(uitslag_parsed)
    except:
        return pd.DataFrame()

# Generate some dummy alle_renners
alle_renners = ["Wout van Aert", "Mathieu van der Poel", "Tadej Pogačar", "Remco Evenepoel"] * 50

# Warm up and load memory
get_uitslagen_old(0, alle_renners)

print("Starting benchmark...")
start = time.time()
df_old = get_uitslagen_old(0, alle_renners)
time_old = time.time() - start
print(f"Old time: {time_old:.4f}s")

start = time.time()
df_new = get_uitslagen_new(0, alle_renners)
time_new = time.time() - start
print(f"New time: {time_new:.4f}s")

print(f"Improvement: {time_old / time_new:.2f}x faster")
assert len(df_old) == len(df_new), "Lengths do not match!"
