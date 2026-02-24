# --- RESULTATEN ---
if st.session_state.selected_riders:
    # Bepaal alle renners die in de tabellen moeten (inclusief de wissels)
    if st.session_state.transfer_plan:
        all_display_riders = st.session_state.selected_riders + st.session_state.transfer_plan['in']
    else:
        all_display_riders = st.session_state.selected_riders

    current_df = df[df['Renner'].isin(all_display_riders)].copy()
    
    # Voeg de rol toe per renner
    def bepaal_rol(naam):
        if st.session_state.transfer_plan:
            if naam in st.session_state.transfer_plan['uit']: return 'Verkopen na PR'
            if naam in st.session_state.transfer_plan['in']: return 'Kopen na PR'
        return 'Basis'
        
    current_df['Rol'] = current_df['Renner'].apply(bepaal_rol)

    # Splits voor budget berekening (start team)
    start_team_df = current_df[current_df['Rol'] != 'Kopen na PR']
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Budget over (Start)", f"€ {max_bud - start_team_df['Prijs'].sum():,.0f}")
    m2.metric("Renners (Start)", f"{len(start_team_df)} / {max_ren}")
    
    if st.session_state.transfer_plan:
        ev_start = start_team_df['EV_early'].sum()
        in_riders_ev = current_df[current_df['Rol'] == 'Kopen na PR']['EV_late'].sum()
        base_riders_late_ev = current_df[current_df['Rol'] == 'Basis']['EV_late'].sum()
        m3.metric("Team EV (Incl. wissels)", f"{ev_start + base_riders_late_ev + in_riders_ev:.0f}")
    else:
        m3.metric("Team EV", f"{start_team_df['Scorito_EV'].sum():.0f}")

    # Kleurfunctie voor de tabellen
    def color_rows(row):
        if row['Rol'] == 'Verkopen na PR':
            return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row) # Rood
        elif row['Rol'] == 'Kopen na PR':
            return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row) # Groen
        return [''] * len(row)

    # 1. MATRIX
    st.header("🗓️ 2. Startlijst Matrix (Seizoensoverzicht)")
    matrix_df = current_df[['Renner', 'Rol'] + race_cols].set_index('Renner')
    
    # Verwijder start-vinkjes als de renner op dat moment niet in je team zit
    if st.session_state.transfer_plan:
        for r in early_races:
            matrix_df.loc[matrix_df['Rol'] == 'Kopen na PR', r] = 0
        for r in late_races:
            matrix_df.loc[matrix_df['Rol'] == 'Verkopen na PR', r] = 0

    # Totalen berekenen (alleen de actieve renners)
    totals = matrix_df[race_cols].sum().astype(int).astype(str)
    totals_row = pd.DataFrame([totals], index=['🏆 TOTAAL AAN DE START'])
    st.dataframe(totals_row, use_container_width=True)

    # Weergave klaarmaken met vinkjes en kleuren
    display_matrix = matrix_df[race_cols].applymap(lambda x: '✅' if x == 1 else '-')
    display_matrix.insert(0, 'Rol', matrix_df['Rol'])
    
    styled_matrix = display_matrix.style.apply(color_rows, axis=1)
    st.dataframe(styled_matrix, use_container_width=True)

    # 2. KOPMAN
    st.header("🥇 3. Kopman Advies (Actieve renners)")
    kop_res = []
    for c in race_cols:
        # Kijk alleen naar renners die de koers rijden én op dat moment in je team zitten
        starters = matrix_df[matrix_df[c] == 1]
        if not starters.empty:
            stat = koers_mapping.get(c, 'AVG')
            # Koppel de statistiek terug uit current_df
            starters_stats = current_df[current_df['Renner'].isin(starters.index)]
            top = starters_stats.sort_values(by=[stat, 'AVG'], ascending=False)['Renner'].tolist()
            kop_res.append({"Koers": c, "K1": top[0] if len(top)>0 else "-", "K2": top[1] if len(top)>1 else "-", "K3": top[2] if len(top)>2 else "-"})
    st.dataframe(pd.DataFrame(kop_res), hide_index=True, use_container_width=True)

    # 3. STATS
    st.header("📊 4. Team Statistieken")
    stats_overzicht = current_df[['Renner', 'Rol', 'COB', 'HLL', 'SPR', 'AVG', 'Prijs', 'EV_early', 'EV_late', 'Scorito_EV']]
    styled_stats = stats_overzicht.sort_values(by=['Rol', 'Scorito_EV'], ascending=[True, False]).style.apply(color_rows, axis=1)
    st.dataframe(styled_stats, hide_index=True, use_container_width=True)
