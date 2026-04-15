import streamlit as st
from supabase import create_client
import logging

logger = logging.getLogger(__name__)

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        st.error("Een databasefout is opgetreden. Probeer het later opnieuw.")
        st.stop()
