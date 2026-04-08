import pandas as pd
import time
from benchmark_get_uitslagen import get_uitslagen_old, get_uitslagen_new

df_raw = pd.DataFrame({
    'Race': ['OHN', 'SB', 'RVB'] * 1000,
    'Rnk': [1, 2, 'DNS'] * 1000,
    'Rider': ['Wout van Aert', 'Mathieu van der Poel', 'Tadej Pogacar'] * 1000
})
df_raw.to_csv("uitslagen.csv", index=False)

alle_renners = ["Wout van Aert", "Mathieu van der Poel", "Tadej Pogačar", "Remco Evenepoel"] * 50

start = time.time()
df_old = get_uitslagen_old(0, alle_renners)
time_old = time.time() - start
print(f"Old time: {time_old:.4f}s")

start = time.time()
df_new = get_uitslagen_new(0, alle_renners)
time_new = time.time() - start
print(f"New time: {time_new:.4f}s")
