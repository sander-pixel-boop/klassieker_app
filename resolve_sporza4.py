import re

with open('pages/Klassiekers - Sporza.py', 'r') as f:
    content = f.read()

pattern1 = r"<<<<<<< HEAD\n            st.divider\(\)\n            st.title\(\"🚴 Sporza AI Coach\"\)\n            ev_method = st.selectbox\(\"🧮 Rekenmodel \(EV\)\", \[\"1. Sporza Ranking \(Dynamisch\)\", \"2. Originele Curve \(Macht 4\)\"\]\)\n            toon_uitslagen = st.checkbox\(\"🏁 Koersen zijn begonnen \(Toon uitslagen\)\", value=True\)\n        \n            st.divider\(\)\n            st.markdown\(\"### 🔁 Transfer Strategie\"\)\n            num_transfers = st.slider\(\"Aantal geplande transfers\", 0, 5, 0\)\n        \n            t_moments = \[\]\n            if num_transfers > 0:\n                st.write\(\"Wanneer wil je de wissels inzetten\?\"\)\n                for i in range\(num_transfers\):\n                    default_idx = min\(len\(available_races\)-2, 13\)\n                    moment = st.selectbox\(f\"Wissel \{i\+1\} ná:\", options=available_races\[:-1\], index=default_idx, key=f\"t_\{i\}\"\)\n                    t_moments.append\(moment\)\n                \n                t_moments = sorted\(t_moments, key=lambda x: available_races.index\(x\)\)\n=======\n    save_data = \{\"selected_riders\": st.session_state.sporza_selected_riders, \"transfer_plan\": st.session_state.sporza_transfer_plan\}\n    st.download_button\(\"📥 Download als .JSON\", data=json.dumps\(save_data\), file_name=f\"\{speler_naam\}_sporza_team.json\", mime=\"application/json\", use_container_width=True\)\n    \n    uploaded_file = st.file_uploader\(\"📂 Upload Team \(.json\)\", type=\"json\"\)\n    if uploaded_file is not None and st.button\(\"Laad .json in\", use_container_width=True\):\n        try:\n            ld = json.load\(uploaded_file\)\n            st.session_state.sporza_selected_riders = ld.get\(\"selected_riders\", \[\]\)\n            st.session_state.sporza_transfer_plan = ld.get\(\"transfer_plan\", \[\]\)\n            st.success\(\"✅ Lokaal bestand geladen!\"\)\n            st.rerun\(\)\n        except Exception as e:\n            st.error\(f\"Fout bij inladen: \{e\}\"\)\n\n    st.divider\(\)\n    st.title\(\"🚴 Sporza AI Coach\"\)\n    ev_method = st.selectbox\(\"🧮 Rekenmodel \(EV\)\", \[\"1. Sporza Ranking \(Dynamisch\)\", \"2. Originele Curve \(Macht 4\)\"\]\)\n    toon_uitslagen = st.checkbox\(\"🏁 Koersen zijn begonnen \(Toon uitslagen\)\", value=True\)\n\n    st.divider\(\)\n    st.markdown\(\"### 🔁 Transfer Strategie\"\)\n    num_transfers = st.slider\(\"Aantal geplande transfers\", 0, 5, 0, help=\"Selecteer het aantal transfers dat je wilt plannen voor de berekening.\"\)\n\n    t_moments = \[\]\n    if num_transfers > 0:\n        st.write\(\"Wanneer wil je de wissels inzetten\?\"\)\n        for i in range\(num_transfers\):\n            default_idx = min\(len\(available_races\)-2, 13\)\n            moment = st.selectbox\(f\"Wissel \{i\+1\} ná:\", options=available_races\[:-1\], index=default_idx, key=f\"t_\{i\}\"\)\n            t_moments.append\(moment\)"

replace1 = r"""            st.divider()
            st.title("🚴 Sporza AI Coach")
            ev_method = st.selectbox("🧮 Rekenmodel (EV)", ["1. Sporza Ranking (Dynamisch)", "2. Originele Curve (Macht 4)"])
            toon_uitslagen = st.checkbox("🏁 Koersen zijn begonnen (Toon uitslagen)", value=True)

            st.divider()
            st.markdown("### 🔁 Transfer Strategie")
            num_transfers = st.slider("Aantal geplande transfers", 0, 5, 0, help="Selecteer het aantal transfers dat je wilt plannen voor de berekening.")

            t_moments = []
            if num_transfers > 0:
                st.write("Wanneer wil je de wissels inzetten?")
                for i in range(num_transfers):
                    default_idx = min(len(available_races)-2, 13)
                    moment = st.selectbox(f"Wissel {i+1} ná:", options=available_races[:-1], index=default_idx, key=f"t_{i}")
                    t_moments.append(moment)

                t_moments = sorted(t_moments, key=lambda x: available_races.index(x))"""

content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)

with open('pages/Klassiekers - Sporza.py', 'w') as f:
    f.write(content)
