import pulp
import pandas as pd

def solve_giro_team(df, draft_counts=None, max_bud=100.0, max_ren=16, max_per_team=None, force_base=None, ban_base=None, ev_column='EV'):
    prob = pulp.LpProblem("Sporza_Giro_Solver", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("Select", df.index, cat='Binary')

    df_solve = df.copy()

    if draft_counts is not None:
        df_solve['Draft_Pts'] = df_solve['Renner'].map(draft_counts).fillna(0)
        df_solve['Obj_Score'] = (df_solve['Draft_Pts'] * 1000) + df_solve[ev_column]
    else:
        df_solve['Obj_Score'] = df_solve[ev_column]

    prob += pulp.lpSum([df_solve.loc[i, 'Obj_Score'] * x[i] for i in df_solve.index])
    prob += pulp.lpSum([x[i] for i in df_solve.index]) == max_ren
    prob += pulp.lpSum([df_solve.loc[i, 'Prijs'] * x[i] for i in df_solve.index]) <= max_bud

    if max_per_team is not None and 'Team' in df_solve.columns:
        for team in df_solve['Team'].dropna().unique():
            team_indices = df_solve[df_solve['Team'] == team].index
            prob += pulp.lpSum([x[i] for i in team_indices]) <= max_per_team

    if force_base or ban_base:
        for i in df_solve.index:
            renner = df_solve.loc[i, 'Renner']
            if force_base and renner in force_base: prob += x[i] == 1
            if ban_base and renner in ban_base:   prob += x[i] == 0

    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=15))
    if pulp.LpStatus[prob.status] == 'Optimal':
        return [df_solve.loc[i, 'Renner'] for i in df_solve.index if x[i].varValue > 0.5]
    return []
