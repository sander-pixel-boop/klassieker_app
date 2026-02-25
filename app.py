import streamlit as st

st.set_page_config(
    page_title="Wieler Spellen Solver",
    page_icon="🚴‍♂️",
)

st.write("# Welkom bij de Wieler Spellen Solver! 🚴‍♂️")

st.markdown(
    """
    Dit is jouw centrale dashboard voor het berekenen van de ultieme selecties voor de voorjaarsklassiekers en grote ronden.
    
    👈 **Kies een spel in het menu aan de linkerkant om te beginnen!**
    
    ### Beschikbare Solvers:
    * **🏆 Scorito Klassiekers:** Optimaliseer je selectie met het 45M budget en bereken de perfecte wisselstrategie na Parijs-Roubaix.
    * **🦁 Sporza Wielermanager (WIP):** Bouw je team binnen de limieten van 120M, 20 renners en maximaal 4 per ploeg.
    * *Binnenkort: Scorito en Sporza voor de Grote Ronden!*
    """
)
