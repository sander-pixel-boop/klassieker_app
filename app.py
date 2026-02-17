import streamlit as st
import pandas as pd

st.title("Mijn Scorito Klassieker Hulp")

# Stap 1: Budget instellen
budget = st.number_input("Wat is je budget?", value=46000000, step=500000)

# Stap 2: Data invoeren (dit kun je later vervangen door een Excel upload)
st.write("Hieronder een voorbeeldlijstje. Dit moet je later vullen met echte data.")

data = {
    'Renner': ['Van der Poel', 'Van Aert', 'Pogacar', 'Pedersen', 'Philipsen'],
    'Prijs': [6000000, 5000000, 5500000, 4000000, 4500000],
    'Punten_Verwachting': [1000, 950, 980, 800, 850]
}
df = pd.DataFrame(data)

# Laat de tabel zien
st.dataframe(df)

# Simpele berekening
st.write(f"Je hebt nog {(budget - df['Prijs'].sum())/1000000:.1f} miljoen over als je deze 5 kiest.")
