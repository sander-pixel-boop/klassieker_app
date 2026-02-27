import streamlit as st

st.set_page_config(
    page_title="Wieler Spellen Solver",
    page_icon="🚴‍♂️",
)

st.write("# Welkom bij de Wieler Spellen Solver! 🚴‍♂️")

st.write("# De tool combineert data uit twee externe bronnen:
    * **[Wielerorakel](https://www.cyclingoracle.com/):** Levert de AI-gebaseerde *Skill-scores* (0 tot 100) van renners op specifieke terreinen zoals Kasseien (COB), Heuvels (HLL) en Sprints (SPR).
    * **[Kopmanpuzzel](https://kopmanpuzzel.up.railway.app/) (via Gebruiker):** Levert de voorlopige startlijsten en de actuele Scorito-prijzen.")

st.markdown(
    """
    Dit is jouw centrale dashboard voor het berekenen van de ultieme selecties voor de voorjaarsklassiekers en grote ronden.
    
    👈 **Kies een spel in het menu aan de linkerkant om te beginnen!**
    
    ### Beschikbare Solvers:
    * **Scorito Klassiekers:** Optimaliseer je selectie met het 45M budget en bereken de perfecte wisselstrategie na Parijs-Roubaix.
    * **🚧 **WORK IN PROGRESS (WIP)** 🚧 Sporza Wielermanager:** Bouw je team binnen de limieten van 120M, 20 renners en maximaal 4 per ploeg.
    * *Binnenkort: Scorito en Sporza voor de Grote Ronden!*
    """
)
