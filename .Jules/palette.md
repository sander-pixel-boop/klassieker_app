## 2024-05-18 - [Add help tooltips for complex configurations]
**Learning:** Streamlit's native `help=` parameter provides non-blocking, inline contextual guidance that is highly effective for explaining complex settings (like algorithm choices and game rules) without overwhelming the main UI layout.
**Action:** Systematically apply `help=` tooltips to primary configuration inputs (`st.selectbox`, `st.checkbox`, `st.slider`) across all game dashboards to improve usability and reduce cognitive load for new users.

## 2024-06-25 - [Add help tooltips for disabled states]
**Learning:** Users can often be confused when buttons are disabled without an explanation, reducing usability and making the UI seem unresponsive or broken. Adding contextual tooltips to disabled buttons using Streamlit's `help=` parameter significantly improves clarity.
**Action:** Always add a `help=` parameter to `st.button` when it uses a `disabled=` state to explain exactly *why* the action cannot be performed right now.
