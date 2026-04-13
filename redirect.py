import streamlit as st

nieuwe_url = "https://wielerspelhelper.streamlit.app"

st.set_page_config(page_title="App Verhuisd", page_icon="🚀")

st.warning(f"⚠️ De Wielermanager AI is verhuisd naar een nieuwe link:\n\n**[{nieuwe_url}]({nieuwe_url})**")
st.write("Sla de nieuwe link op in je favorieten. Je wordt over 5 seconden automatisch doorgestuurd.")

# Automatische redirect (HTML/JS)
redirect_code = f"""
<meta http-equiv="refresh" content="5; url='{nieuwe_url}'">
<script>
    setTimeout(function() {{
        window.parent.location.href = '{nieuwe_url}';
    }}, 5000);
</script>
"""
st.markdown(redirect_code, unsafe_allow_html=True)
