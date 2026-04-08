import re

with open('pages/Klassiekers - Sporza.py', 'r') as f:
    content = f.read()

# Pattern 1
pattern1 = r"<<<<<<< HEAD\n        s = \{'Kassei': cob, 'Heuvel': hll, 'Sprint': spr, 'Klimmer': int\(row\.get\('MTN', 0\) or 0\), 'Tijdrit': int\(row\.get\('ITT', 0\) or 0\), 'Klassement': int\(row\.get\('GC', 0\) or 0\)\}\n        if sum\(s\.values\(\)\) == 0: return None\n        \n        # Check for ties\n        max_val = max\(s\.values\(\)\)\n        max_keys = \[k for k, v in s\.items\(\) if v == max_val\]\n        if len\(max_keys\) > 1:\n            return None\n=======\n        s = \{'Kassei': cob, 'Heuvel': hll, 'Sprint': spr, 'Klimmer': mtn, 'Tijdrit': itt, 'Klassement': gc\}\n        if sum\(s\.values\(\)\) == 0: return 'Onbekend'\n>>>>>>> origin/main"

replace1 = r"""        s = {'Kassei': cob, 'Heuvel': hll, 'Sprint': spr, 'Klimmer': int(row.get('MTN', 0) or 0), 'Tijdrit': int(row.get('ITT', 0) or 0), 'Klassement': int(row.get('GC', 0) or 0)}
        if sum(s.values()) == 0: return None

        # Check for ties
        max_val = max(s.values())
        max_keys = [k for k, v in s.items() if v == max_val]
        if len(max_keys) > 1:
            return None"""

content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)


# Pattern 2
pattern2 = r"<<<<<<< HEAD\n            st.divider\(\)\n            st.title\(\"🚴 Sporza AI Coach\"\)\n            ev_method = st.selectbox\(\"🧮 Rekenmodel \(EV\)\", \[\"1. Sporza Ranking \(Dynamisch\)\", \"2. Originele Curve \(Macht 4\)\"\]\)\n            toon_uitslagen = st.checkbox\(\"🏁 Koersen zijn begonnen \(Toon uitslagen\)\", value=True\)\n        \n            st.divider\(\)\n            st.markdown\(\"### 🔁 Transfer Strategie\"\)\n            num_transfers = st.slider\(\"Aantal geplande transfers\", 0, 5, 0\)\n        \n            t_moments = \[\]\n            if num_transfers > 0:\n                st.write\(\"Wanneer wil je de wissels inzetten\?\"\)\n                for i in range\(num_transfers\):\n                    default_idx = min\(len\(available_races\)-2, 13\)\n                    moment = st.selectbox\(f\"Wissel \{i\+1\} ná:\", options=available_races\[:-1\], index=default_idx, key=f\"t_\{i\}\"\)\n                    t_moments.append\(moment\)\n                \n                t_moments = sorted\(t_moments, key=lambda x: available_races.index\(x\)\)\n=======\n    save_data = \{\"selected_riders\": st.session_state.sporza_selected_riders, \"transfer_plan\": st.session_state.sporza_transfer_plan\}\n    st.download_button\(\"📥 Download als .JSON\", data=json.dumps\(save_data\), file_name=f\"\{speler_naam\}_sporza_team.json\", mime=\"application/json\", use_container_width=True\)\n    \n    uploaded_file = st.file_uploader\(\"📂 Upload Team \(.json\)\", type=\"json\"\)\n    if uploaded_file is not None and st.button\(\"Laad .json in\", use_container_width=True\):\n        try:\n            ld = json.load\(uploaded_file\)\n            st.session_state.sporza_selected_riders = ld.get\(\"selected_riders\", \[\]\)\n            st.session_state.sporza_transfer_plan = ld.get\(\"transfer_plan\", \[\]\)\n            st.success\(\"✅ Lokaal bestand geladen!\"\)\n            st.rerun\(\)\n        except Exception as e:\n            st.error\(f\"Fout bij inladen: \{e\}\"\)\n\n    st.divider\(\)\n    st.title\(\"🚴 Sporza AI Coach\"\)\n    ev_method = st.selectbox\(\"🧮 Rekenmodel \(EV\)\", \[\"1. Sporza Ranking \(Dynamisch\)\", \"2. Originele Curve \(Macht 4\)\"\]\)\n    toon_uitslagen = st.checkbox\(\"🏁 Koersen zijn begonnen \(Toon uitslagen\)\", value=True\)\n\n    st.divider\(\)\n    st.markdown\(\"### 🔁 Transfer Strategie\"\)\n    num_transfers = st.slider\(\"Aantal geplande transfers\", 0, 5, 0\)\n\n    t_moments = \[\]\n    if num_transfers > 0:\n        st.write\(\"Wanneer wil je de wissels inzetten\?\"\)\n        for i in range\(num_transfers\):\n            default_idx = min\(len\(available_races\)-2, 13\)\n            moment = st.selectbox\(f\"Wissel \{i\+1\} ná:\", options=available_races\[:-1\], index=default_idx, key=f\"t_\{i\}\"\)\n            t_moments.append\(moment\)\n>>>>>>> origin/main"

replace2 = r"""    save_data = {"selected_riders": st.session_state.sporza_selected_riders, "transfer_plan": st.session_state.sporza_transfer_plan}
    st.download_button("📥 Download als .JSON", data=json.dumps(save_data), file_name=f"{speler_naam}_sporza_team.json", mime="application/json", use_container_width=True)

    uploaded_file = st.file_uploader("📂 Upload Team (.json)", type="json")
    if uploaded_file is not None and st.button("Laad .json in", use_container_width=True):
        try:
            ld = json.load(uploaded_file)
            st.session_state.sporza_selected_riders = ld.get("selected_riders", [])
            st.session_state.sporza_transfer_plan = ld.get("transfer_plan", [])
            st.success("✅ Lokaal bestand geladen!")
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij inladen: {e}")

    st.divider()
    st.title("🚴 Sporza AI Coach")
    ev_method = st.selectbox("🧮 Rekenmodel (EV)", ["1. Sporza Ranking (Dynamisch)", "2. Originele Curve (Macht 4)"])
    toon_uitslagen = st.checkbox("🏁 Koersen zijn begonnen (Toon uitslagen)", value=True)

    st.divider()
    st.markdown("### 🔁 Transfer Strategie")
    num_transfers = st.slider("Aantal geplande transfers", 0, 5, 0)

    t_moments = []
    if num_transfers > 0:
        st.write("Wanneer wil je de wissels inzetten?")
        for i in range(num_transfers):
            default_idx = min(len(available_races)-2, 13)
            moment = st.selectbox(f"Wissel {i+1} ná:", options=available_races[:-1], index=default_idx, key=f"t_{i}")
            t_moments.append(moment)

        t_moments = sorted(t_moments, key=lambda x: available_races.index(x))"""

content = re.sub(pattern2, replace2, content, flags=re.MULTILINE)

# Pattern 3
pattern3 = r"<<<<<<< HEAD\n                new_col.append\(get_numeric_status\(is_on_list, is_on_list, is_verreden, rank_str\)\)\n            d_df\[c\] = pd.to_numeric\(new_col\)\n=======\n                \n                display_matrix.loc\[r, c\] = get_numeric_status\(is_on_list, is_starter, is_verreden, rank_str\)\n            display_matrix\[c\] = pd.to_numeric\(display_matrix\[c\]\)\n\n        display_matrix.insert\(0, 'Rol', matrix_df\['Rol'\]\)\n        \n        for t in st.session_state.sporza_transfer_plan:\n            moment = t\['moment'\]\n            if moment in display_matrix.columns and f'🔁 \{moment\}' not in display_matrix.columns:\n                idx = display_matrix.columns.get_loc\(moment\) \+ 1\n                display_matrix.insert\(idx, f'🔁 \{moment\}', '\|'\)\n\n        def color_rows\(data\):\n            styles = pd.DataFrame\('', index=data.index, columns=data.columns\)\n            verkocht_mask = data\['Rol'\].astype\(str\).str.contains\('Verkocht', na=False\)\n            gekocht_mask = data\['Rol'\].astype\(str\).str.contains\('Gekocht', na=False\)\n            styles.loc\[verkocht_mask, :\] = 'background-color: rgba\(255, 99, 71, 0.2\)'\n            styles.loc\[gekocht_mask, :\] = 'background-color: rgba\(144, 238, 144, 0.2\)'\n            return styles\n\n        format_dict = \{c: lambda x: format_race_status\(x, 30\) for c in available_races\}\n        st.dataframe\(display_matrix.style.apply\(color_rows, axis=None\).format\(format_dict\), use_container_width=True\)\n\n    with tab3:\n        st.header\(\"👑 Kopmannen Advies\"\)\n        st.write\(\"In Sporza kies je slechts \*\*1 kopman\*\* per koers voor bonuspunten. Hier is de beste keuze uit jouw geselecteerde 12 starters.\"\)\n        \n            if is_verreden:\n                res = df_k\[df_k\['Renner'\] == r\]\n                if not res.empty: rank_str = res\['Rnk'\].values\[0\]\n            new_col.append\(get_numeric_status\(is_on_list, is_on_list, is_verreden, rank_str\)\)\n        d_df\[c\] = pd.to_numeric\(new_col\)\n>>>>>>> origin/main"

replace3 = r"""                new_col.append(get_numeric_status(is_on_list, is_on_list, is_verreden, rank_str))
            d_df[c] = pd.to_numeric(new_col)"""

content = re.sub(pattern3, replace3, content, flags=re.MULTILINE)

with open('pages/Klassiekers - Sporza.py', 'w') as f:
    f.write(content)
