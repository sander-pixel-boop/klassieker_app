import pandas as pd

df = pd.DataFrame({'Prijs': [1, 2, 3]})
df['Prijs'] = pd.to_numeric(df['Prijs'], errors='coerce').fillna(0)
df.loc[df['Prijs'] == 2, 'Prijs'] = 0.75
print(df)
