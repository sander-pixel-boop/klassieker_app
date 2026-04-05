import pandas as pd
import numpy as np

df = pd.DataFrame({'Prijs': [1, 2, 3]})
df['Prijs'] = pd.to_numeric(df['Prijs'], errors='coerce').fillna(0)
# Make it integer to simulate the problem
df['Prijs'] = df['Prijs'].astype(int)

try:
    df.loc[df['Prijs'] == 2, 'Prijs'] = 0.75
except Exception as e:
    print(f"Error: {e}")
