# --- OPSLAAN / LADEN BLOK ---
        st.divider()
        with st.expander("💾 Team Opslaan / Inladen"):
            if st.session_state.selected_riders:
                save_data = {
                    "selected_riders": st.session_state.selected_riders,
                    "transfer_plan": st.session_state.transfer_plan
                }
                json_str = json.dumps(save_data)
                st.download_button(
                    label="📥 Download huidig team",
                    data=json_str,
                    file_name="scorito_team.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            uploaded_file = st.file_uploader("📂 Upload een bewaard team (.json)", type="json")
            if uploaded_file is not None:
                if st.button("Laad Team in", use_container_width=True):
                    try:
                        loaded_data = json.load(uploaded_file)
                        oude_selectie = loaded_data.get("selected_riders", [])
                        oud_plan = loaded_data.get("transfer_plan", None)
                        
                        huidige_renners = df['Renner'].tolist()
                        
                        def update_naam(naam):
                            if naam in huidige_renners: return naam
                            match = process.extractOne(naam, huidige_renners, scorer=fuzz.token_set_ratio)
                            return match[0] if match and match[1] > 80 else naam

                        st.session_state.selected_riders = [update_naam(r) for r in oude_selectie]
                        
                        if oud_plan:
                            st.session_state.transfer_plan = {
                                "uit": [update_naam(r) for r in oud_plan.get("uit", [])],
                                "in": [update_naam(r) for r in oud_plan.get("in", [])]
                            }
                        else:
                            st.session_state.transfer_plan = None
                            
                        st.session_state.last_finetune = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fout bij inladen: {e}")
