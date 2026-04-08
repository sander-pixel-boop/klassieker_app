import sys
import time
from unittest.mock import MagicMock

sys.modules['streamlit'] = MagicMock()
sys.modules['utils.db'] = MagicMock()

from pages.Sporza_Giro_Evaluator import match_naam_cached, normalize_name

alle_renners = [f"Renner {i}" for i in range(1000)]
alle_renners_tuple = tuple(alle_renners)

# warm up normalize_name cache
for r in alle_renners:
    normalize_name(r)

match_naam_cached.cache_clear()

start = time.time()
for i in range(1000):
    match_naam_cached(f"Unmatched {i}", alle_renners_tuple)
end = time.time()

print(f"Baseline Time: {end - start:.4f} seconds")
