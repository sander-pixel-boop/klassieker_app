import pandas as pd
import numpy as np
import time

# Create a large dummy dataframe
np.random.seed(42)
n_rows = 10000
n_cols = 20

data = {
    'Rol': np.random.choice(['Verkocht na X', 'Gekocht na Y', 'Basis (Blijft)'], n_rows)
}
for i in range(n_cols):
    data[f'Col{i}'] = np.random.randn(n_rows)

df = pd.DataFrame(data)

def color_rows(row):
    if 'Verkocht' in row['Rol']: return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row)
    if 'Gekocht' in row['Rol']: return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row)
    return [''] * len(row)

start = time.time()
df.style.apply(color_rows, axis=1).to_html() # We use to_html to force evaluation of the style
end = time.time()
print(f"Row-by-row apply: {end - start:.4f} seconds")

def style_dataframe(data):
    styles = pd.DataFrame('', index=data.index, columns=data.columns)
    # Using numpy where for faster assignment, or loc
    verkocht_mask = data['Rol'].str.contains('Verkocht', na=False)
    gekocht_mask = data['Rol'].str.contains('Gekocht', na=False)

    styles.loc[verkocht_mask, :] = 'background-color: rgba(255, 99, 71, 0.2)'
    styles.loc[gekocht_mask, :] = 'background-color: rgba(144, 238, 144, 0.2)'
    return styles

start = time.time()
df.style.apply(style_dataframe, axis=None).to_html()
end = time.time()
print(f"Vectorized apply: {end - start:.4f} seconds")
