import streamlit as st
import pandas as pd
import pulp
import io
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Scorito Manager Pro", layout="wide", page_icon="🚴")

# --- 1. DATA: PRIJZEN (Gescand uit jouw screenshots) ---
PRICES_CSV = """Naam,Prijs
T. Pogačar,7000000
M. van der Poel,6000000
J. Philipsen,5000000
M. Pedersen,4500000
W. van Aert,4500000
J. Milan,3500000
T. Pidcock,3000000
M. Brennan,3000000
A. De Lie,2500000
C. Laporte,2500000
T. Benoot,2500000
T. Wellens,2500000
M. Jorgenson,2500000
T. Merlier,2500000
R. Evenepoel,2500000
F. Ganna,2000000
O. Kooij,2000000
B. Healy,2000000
P. Magnier,2000000
J. Stuyven,1500000
S. Küng,1500000
F. Vermeersch,1500000
N. Politt,1500000
N. Powless,1500000
M. Matthews,1500000
B. Girmay,1500000
M. Bjerg,1500000
M. Mohorič,1500000
R. Grégoire,1500000
M. Skjelmose,1500000
B. Cosnefroy,1500000
K. Groves,1500000
M. Vacek,1500000
T. Skujiņš,1000000
M. Teunissen,1000000
M. Trentin,1000000
J. Narváez,1000000
S. Dillier,1000000
J. Meeus,1000000
D. van Poppel,1000000
T. Nys,1000000
K. Vauquelin,1000000
J. Almeida,1000000
I. del Toro,1000000
A. Yates,1000000
B. McNulty,1000000
F. Großschartner,1000000
P. Bittner,1000000
M. Van Gils,1000000
J. Vingegaard,1000000
G. Vermeersch,750000
D. van Baarle,750000
L. Mozzato,750000
V. Madouas,750000
L. Pithie,750000
D. Teuns,750000
H. Hofstetter,750000
L. Rex,750000
F. Wright,750000
D. Ballerini,750000
S. Wærenskjold,750000
E. Planckaert,750000
M. Gogl,750000
F. Sénéchal,750000
S. Kragh Andersen,750000
G. Ciccone,750000
M. van den Berg,750000
A. Laurance,750000
A. Zingle,750000
O. Riesebeek,750000
L. Martinez,750000
L. Van Eetvelt,750000
O. Onley,750000
T. Bayer,750000
Y. Lampaert,500000
R. Tiller,500000
A. Turgis,500000
J. Degenkolb,500000
B. Turner,500000
K. Asgreen,500000
J. Alaphilippe,500000
J. Tratnik,500000
M. Cort,500000
M. Hoelgaard,500000
E. Theuns,500000
S. Bissegger,500000
J. Rutsch,500000
P. Eenkhoorn,500000
P. Allegaert,500000
M. Valgren,500000
B. Van Lerberghe,500000
C. Bol,500000
I. García Cortina,500000
O. Doull,500000
J. Abrahamsen,500000
O. Naesen,500000
M. Haller,500000
Q. Simmons,500000
M. Louvel,500000
A. Lutsenko,500000
J. Stewart,500000
B. Jungels,500000
T. van der Hoorn,500000
J. Biermans,500000
J. Jacobs,500000
M. Kwiatkowski,500000
M. Walscheid,500000
J. De Buyst,500000
T. Van Asbroeck,500000
G. Moscon,500000
A. Capiot,500000
L. Durbridge,500000
T. Roosen,500000
M. Hirschi,500000
A. Bettiol,500000
P. Roglič,500000
A. Aranburu,500000
A. Bagioli,500000
J. Haig,500000
A. Vlasov,500000
V. Lafay,500000
Q. Hermans,500000
M. Schmid,500000
P. Bilbao,500000
S. Buitrago,500000
D. Martínez,500000
P. Konrad,500000
M. Honoré,500000
R. Adrià,500000
G. Martin,500000
C. Canal,500000
Q. Pacher,500000
T. Geoghegan Hart,500000
B. Mollema,500000
N. Schultz,500000
A. Covi,500000
W. Barguil,500000
W. Kelderman,500000
A. Kron,500000
S. Higuita,500000
A. Kirsch,500000
X. Meurisse,500000
S. Velasco,500000
C. Strong,500000
V. Albanese,500000
A. De Gendt,500000
M. Menten,500000
D. Formolo,500000
A. Segaert,500000
M. Landa,500000
T. Foss,500000
E. Hayter,500000
J. Mosca,500000
D. Van Gestel,500000
A. Vendrame,500000
S. Bennett,500000
A. Kamp,500000
S. Battistella,500000
J. Steimle,500000
M. Schachmann,500000
I. Van Wilder,500000
D. Caruso,500000
M. Govekar,500000
B. Coquard,500000
I. Izagirre,500000
B. Thomas,500000
F. Gall,500000
G. Mühlberger,500000
R. Carapaz,500000
D. Gaudu,500000
T. Gruel,500000
R. Molard,500000
E. Bernal,500000
D. Godon,500000
M. Sobrero,500000
L. Rota,500000
L. Taminiaux,500000
G. Zimmermann,500000
G. Serrano,500000
N. Tesfatsion,500000
G. Bennett,500000
S. Clarke,500000
K. Neilands,500000
D. Smith,500000
S. Williams,500000
E. Dunbar,500000
J. Hindley,500000
K. Bouwman,500000
F. Engelhardt,500000
N. Eekhoff,500000
W. Poels,500000
A. Charmig,500000
N. Conci,500000
D. Ulissi,500000"""

# --- 2. DATA: WIELERORAKEL (Uit jouw bestand) ---
# Ik heb de belangrijkste kolommen uit je CSV gehaald
WIELERORAKEL_RAW = """Naam,COB,HLL,MTN,SPR,OR
Tadej Pogačar,97,99,99,80,99
Jonas Vingegaard,20,91,99,63,20
Remco Evenepoel,20,96,91,67,97
Mathieu van der Poel,99,93,40,85,97
Mads Pedersen,99,91,47,92,96
Jasper Philipsen,93,79,38,99,95
Isaac del Toro,67,96,91,56,97
João Almeida,20,90,96,48,51
Tom Pidcock,87,95,91,68,94
Wout van Aert,96,92,70,91,94
Tim Merlier,68,24,20,99,83
Biniam Girmay,91,90,45,91,91
Christophe Laporte,97,90,45,86,95
Arnaud De Lie,96,91,45,95,95
Mattias Skjelmose,25,93,89,68,92
Ben Healy,28,92,86,55,91
Jonathan Milan,52,55,20,99,84
Olav Kooij,60,61,20,98,82
Tiesj Benoot,93,92,75,64,91
Tim Wellens,92,93,72,65,91
Maxim Van Gils,45,94,84,72,93
Marc Hirschi,30,94,80,78,93
Valentin Madouas,91,92,75,65,91
Matteo Jorgenson,91,90,89,65,91
Stefan Küng,95,78,50,45,90
Benoît Cosnefroy,32,93,65,82,92
Dylan Groenewegen,20,20,20,98,40
Michael Matthews,80,91,60,90,91
Alberto Bettiol,89,90,72,78,90
Matej Mohorič,92,91,60,75,91
Neilson Powless,70,91,85,60,90
Kasper Asgreen,92,85,62,70,89
Fred Wright,88,86,55,80,88
Jasper Stuyven,94,85,50,85,90
Alexander Kristoff,91,70,25,91,87
Thibau Nys,45,91,68,88,88
Dylan van Baarle,95,80,60,40,88
Nils Politt,92,70,50,55,88
Julian Alaphilippe,55,91,75,76,89
Lennert Van Eetvelt,25,90,90,62,85
Laurence Pithie,85,82,45,88,87
Luca Mozzato,88,78,35,88,86
Rasmus Tiller,89,82,40,80,87
Jhonatan Narváez,75,91,72,82,88
Jordi Meeus,55,30,20,95,78
Corbin Strong,55,89,58,91,85
Paul Magnier,45,75,40,94,82
"""

# --- 3. LOGICA ---

def convert_to_short_name(full_name):
    # Verandert "Tadej Pogačar" naar "t. pogačar"
    parts = str(full_name).split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:])}".lower()
    return str(full_name).lower()

def load_all_data():
    # 1. Prijzen
    df_p = pd.read_csv(io.StringIO(PRICES_CSV))
    df_p['Prijs_Clean'] = pd.to_numeric(df_p['Prijs'], errors='coerce').fillna(0)
    df_p['Match_Name'] = df_p['Naam'].str.lower().str.strip()
    
    # 2. WielerOrakel
    df_wo = pd.read_csv(io.StringIO(WIELERORAKEL_RAW))
    # Maak match-naam van de volledige naam
    df_wo['Match_Name'] = df_wo['Naam'].apply(convert_to_short_name)
    
    # 3. Combineer
    merged = pd.merge(df_p, df_wo, on='Match_Name', how='inner', suffixes=('', '_wo'))
    return merged

df = load_all_data()

# --- 4. UI ---
st.title("🏆 Scorito & WielerOrakel Optimalisator")
st.write(f"Data succesvol gekoppeld! **{len(df)} renners** geladen met prijs en kwaliteitscores.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Instellingen")
    budget = st.number_input("Totaal Budget (€)", value=46000000, step=500000)
    
    st.header("2. Strategie per type koers")
    
    st.subheader("Kasseien")
    st.info("Omloop, Kuurne, E3, Gent-W, DDV, Vlaanderen, Roubaix")
    w_cob = st.slider("Weging Kassei (COB)", 0, 10, 8)
    
    st.subheader("Heuvel & Klim")
    st.info("Amstel, Waalse Pijl, Luik, **Parijs-Nice Et. 7 (Klim)**")
    w_hll = st.slider("Weging Heuvel (HLL)", 0, 10, 6)
    w_mtn = st.slider("Weging Klim (MTN)", 0, 10, 4)
    
    st.subheader("Sprint")
    st.info("Scheldeprijs, De Panne, **Tirreno Et. 7 (Massa-sprint)**")
    w_spr = st.slider("Weging Sprint (SPR)", 0, 10, 5)
    
    st.subheader("Algemeen")
    st.info("De 'OR' (One Day Race) score voor algemene klassieker-kwaliteit")
    w_or = st.slider("Weging Eendags (OR)", 0, 10, 5)

# --- SCORE BEREKENEN ---
df['Score'] = (
    (df['COB'] * w_cob) +
    (df['HLL'] * w_hll) +
    (df['MTN'] * w_mtn) +
    (df['SPR'] * w_spr) +
    (df['OR'] * w_or)
)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 Toprenners voor jouw instellingen")
    st.dataframe(
        df[['Naam', 'Prijs_Clean', 'Score', 'COB', 'HLL', 'MTN', 'SPR']].sort_values('Score', ascending=False).head(15),
        column_config={"Prijs_Clean": st.column_config.NumberColumn("Prijs", format="€ %d")}
    )

with col2:
    st.subheader("🚀 Jouw Optimale Team")
    if st.button("Bereken Beste Combinatie (20 renners)"):
        prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
        sel = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
        
        # Doel: Maximaal Score
        prob += pulp.lpSum([df['Score'][i] * sel[i] for i in df.index])
        
        # Beperkingen
        prob += pulp.lpSum([df['Prijs_Clean'][i] * sel[i] for i in df.index]) <= budget
        prob += pulp.lpSum([sel[i] for i in df.index]) == 20
        
        prob.solve()
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            idx = [i for i in df.index if sel[i].varValue == 1]
            team = df.loc[idx]
            
            st.balloons()
            st.success(f"Team gevonden! Totaal besteed: € {team['Prijs_Clean'].sum():,.0f}")
            
            st.dataframe(
                team[['Naam', 'Prijs_Clean', 'COB', 'HLL', 'MTN', 'SPR']].sort_values('Prijs_Clean', ascending=False),
                column_config={
                    "Prijs_Clean": st.column_config.NumberColumn("Prijs", format="€ %d"),
                    "COB": st.column_config.ProgressColumn("Kassei", min_value=0, max_value=100),
                    "HLL": st.column_config.ProgressColumn("Heuvel", min_value=0, max_value=100),
                    "MTN": st.column_config.ProgressColumn("Klim", min_value=0, max_value=100),
                },
                height=600
            )
        else:
            st.error("Kon geen team samenstellen binnen budget met 20 renners.")

# --- PCS STARTLIJSTEN ---
st.divider()
st.subheader("🌐 Live PCS Check")
st.info("Check hieronder of de renners uit de database op de startlijsten staan.")

if st.button("Check Startlijsten via PCS"):
    startlists = scrape_pcs()
    # Maak een simpele check-tabel
    for race, riders in startlists.items():
        df[race] = df['Match_Name'].apply(lambda x: "✅" if x in riders else "")
    
    st.dataframe(df[['Naam'] + list(RACES_URLS.keys())])
