import streamlit as st
import streamlit.components.v1 as components

# --- VUL HIER JE NIEUWE URL IN ---
nieuwe_url = "https://sporza-puzzelmanager-concept.streamlit.app"

st.set_page_config(page_title="App Verhuisd", page_icon="🚀")

st.warning(f"⚠️ De applicatie is verhuisd naar een nieuwe link:\n\n**[{nieuwe_url}]({nieuwe_url})**")
st.info("Sla de nieuwe link op in je favorieten. Je wordt binnen enkele seconden automatisch doorgestuurd.")

# Robuuste JS redirect via components
redirect_code = f"""
<meta http-equiv="refresh" content="3; url='{nieuwe_url}'">
<script>
    setTimeout(function() {{
        window.top.location.href = '{nieuwe_url}';
    }}, 3000);
</script>
"""
components.html(redirect_code, height=0, width=0)
