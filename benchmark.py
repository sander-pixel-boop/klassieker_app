import pandas as pd
import time
import timeit

def match_uitslag_naam(name, renners):
    return name

df_raw_uitslagen = pd.DataFrame({
    'Race': ['OML', 'STR', 'RVB', 'IFF'] * 1000,
    'Rnk': ['1', '2', 'DNS', 'NAN'] * 1000,
    'Rider': ['Rider A', 'Rider B', 'Rider C', 'Rider D'] * 1000
})
alle_renners = []
sporza_naar_scorito_map = {
    'OML': 'OHN', 'STR': 'SB', 'RVB': 'BDP',
    'IFF': 'GW', 'BRP': 'BP', 'AGT': 'AGR', 'WAP': 'WP'
}

def iterrows_method():
    uitslag_parsed = []
    for index, row in df_raw_uitslagen.iterrows():
        koers_origineel = str(row['Race']).strip().upper()
        koers = sporza_naar_scorito_map.get(koers_origineel, koers_origineel)

        rank_str = str(row['Rnk']).strip().upper()
        if rank_str in ['DNS', 'NAN', '']:
            continue

        rider_name = str(row['Rider']).strip()
        gekoppelde_naam = match_uitslag_naam(rider_name, alle_renners)

        uitslag_parsed.append({
            "Race": koers,
            "Rnk": rank_str,
            "Renner": gekoppelde_naam
        })
    return pd.DataFrame(uitslag_parsed)

def itertuples_method():
    uitslag_parsed = []
    for row in df_raw_uitslagen.itertuples(index=False):
        koers_origineel = str(row.Race).strip().upper()
        koers = sporza_naar_scorito_map.get(koers_origineel, koers_origineel)

        rank_str = str(row.Rnk).strip().upper()
        if rank_str in ['DNS', 'NAN', '']:
            continue

        rider_name = str(row.Rider).strip()
        gekoppelde_naam = match_uitslag_naam(rider_name, alle_renners)

        uitslag_parsed.append({
            "Race": koers,
            "Rnk": rank_str,
            "Renner": gekoppelde_naam
        })
    return pd.DataFrame(uitslag_parsed)

def zip_method():
    uitslag_parsed = []
    for race, rnk, rider in zip(df_raw_uitslagen['Race'], df_raw_uitslagen['Rnk'], df_raw_uitslagen['Rider']):
        koers_origineel = str(race).strip().upper()
        koers = sporza_naar_scorito_map.get(koers_origineel, koers_origineel)

        rank_str = str(rnk).strip().upper()
        if rank_str in ['DNS', 'NAN', '']:
            continue

        rider_name = str(rider).strip()
        gekoppelde_naam = match_uitslag_naam(rider_name, alle_renners)

        uitslag_parsed.append({
            "Race": koers,
            "Rnk": rank_str,
            "Renner": gekoppelde_naam
        })
    return pd.DataFrame(uitslag_parsed)

print("Iterrows:", timeit.timeit(iterrows_method, number=10))
print("Itertuples:", timeit.timeit(itertuples_method, number=10))
print("Zip:", timeit.timeit(zip_method, number=10))
