## 2024-05-18 - [Add help tooltips for complex configurations]
**Learning:** Streamlit's native `help=` parameter provides non-blocking, inline contextual guidance that is highly effective for explaining complex settings (like algorithm choices and game rules) without overwhelming the main UI layout.
**Action:** Systematically apply `help=` tooltips to primary configuration inputs (`st.selectbox`, `st.checkbox`, `st.slider`) across all game dashboards to improve usability and reduce cognitive load for new users.
## 2024-05-15 - Disabled Buttons in Streamlit
**Learning:** When using `st.button` with `disabled=True`, users often lack context as to *why* the button is disabled, which can lead to frustration and confusion.
**Action:** Always include a contextual `help=` parameter tooltip on conditionally disabled buttons to clarify the constraint (e.g., "Je bent al bij de eerste etappe." or "Je hebt onvoldoende budget voor deze wissel.").
