import sys
import types
from unittest.mock import MagicMock
import pandas as pd
import importlib.util
import os
import ast

# Mock dependencies
mock_st = MagicMock()
sys.modules['streamlit'] = mock_st
mock_supabase = MagicMock()
sys.modules['supabase'] = mock_supabase

file_path = os.path.join(os.path.dirname(__file__), '..', 'pages', 'Scorito', 'Classics', 'Klassiekers.py')

with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

tree = ast.parse(code)
new_body = []
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
        new_body.append(node)
tree.body = new_body

compiled = compile(tree, filename="<ast>", mode="exec")
namespace = {}
exec(compiled, namespace)

evaluate_plan_ev = namespace['evaluate_plan_ev']

def test_evaluate_plan_ev_basic():
    print("Function loaded:", evaluate_plan_ev)

def test_evaluate_plan_ev_no_transfers():
    df_eval = pd.DataFrame({
        'Renner': ['A', 'B', 'C'],
        'EV_R1': [10, 20, 30],
        'EV_R2': [15, 25, 35]
    })
    base_team = ['A', 'B']
    plan = []
    available_races = ['R1', 'R2']

    # A total = 10 + 15 = 25
    # B total = 20 + 25 = 45
    # Overall = 70

    total_ev = evaluate_plan_ev(df_eval, base_team, plan, available_races)
    assert total_ev == 70

def test_evaluate_plan_ev_with_transfers():
    df_eval = pd.DataFrame({
        'Renner': ['A', 'B', 'C'],
        'EV_R1': [10, 20, 30],
        'EV_R2': [15, 25, 35],
        'EV_R3': [20, 30, 40]
    })
    base_team = ['A', 'B']
    # A transfer happens *before* or *after* the race?
    # Based on the code:
    # for t in plan:
    #     if t['moment'] == race:
    #         if t['uit'] in current_active: current_active.remove(t['uit'])
    #         current_active.add(t['in'])
    # This means for `race`, the transfer IS applied. So if moment == 'R2', C replaces B for R2 and R3.

    plan = [{'uit': 'B', 'in': 'C', 'moment': 'R2'}]
    available_races = ['R1', 'R2', 'R3']

    # R1: A (10) + B (20) = 30
    # R2: A (15) + C (35) = 50 (since transfer happens at R2)
    # R3: A (20) + C (40) = 60
    # Overall = 140

    total_ev = evaluate_plan_ev(df_eval, base_team, plan, available_races)
    assert total_ev == 140

def test_evaluate_plan_ev_transfer_chain():
    df_eval = pd.DataFrame({
        'Renner': ['A', 'B', 'C', 'D'],
        'EV_R1': [10, 20, 0, 0],
        'EV_R2': [10, 0, 30, 0],
        'EV_R3': [10, 0, 0, 40]
    })
    base_team = ['A', 'B']
    # B -> C at R2, C -> D at R3
    plan = [
        {'uit': 'B', 'in': 'C', 'moment': 'R2'},
        {'uit': 'C', 'in': 'D', 'moment': 'R3'}
    ]
    available_races = ['R1', 'R2', 'R3']

    # R1: A (10) + B (20) = 30
    # R2: A (10) + C (30) = 40
    # R3: A (10) + D (40) = 50
    # Overall = 120

    total_ev = evaluate_plan_ev(df_eval, base_team, plan, available_races)
    assert total_ev == 120

def test_evaluate_plan_ev_rider_not_found():
    df_eval = pd.DataFrame({
        'Renner': ['A'],
        'EV_R1': [10]
    })
    base_team = ['A', 'B'] # B not in df
    plan = []
    available_races = ['R1']

    # A total = 10
    # B total = 0 (empty res)
    # Overall = 10

    total_ev = evaluate_plan_ev(df_eval, base_team, plan, available_races)
    assert total_ev == 10


def test_evaluate_plan_ev_empty_base():
    df_eval = pd.DataFrame({
        'Renner': ['A'],
        'EV_R1': [10]
    })
    base_team = []
    plan = [{'uit': 'A', 'in': 'A', 'moment': 'R1'}]
    available_races = ['R1']

    # Empty base means A is not in the team.
    # The code handles t['uit'] by removing it ONLY IF it's in current_active:
    # `if t['uit'] in current_active: current_active.remove(t['uit'])`
    # Since A is not in the team, it adds A at R1.

    total_ev = evaluate_plan_ev(df_eval, base_team, plan, available_races)
    assert total_ev == 10

def test_evaluate_plan_ev_multiple_transfers_same_moment():
    df_eval = pd.DataFrame({
        'Renner': ['A', 'B', 'C', 'D'],
        'EV_R1': [10, 20, 0, 0],
        'EV_R2': [10, 0, 30, 40]
    })
    base_team = ['A', 'B']
    # A->C, B->D at R2
    plan = [
        {'uit': 'A', 'in': 'C', 'moment': 'R2'},
        {'uit': 'B', 'in': 'D', 'moment': 'R2'}
    ]
    available_races = ['R1', 'R2']

    # R1: A (10) + B (20) = 30
    # R2: C (30) + D (40) = 70
    # Overall = 100

    total_ev = evaluate_plan_ev(df_eval, base_team, plan, available_races)
    assert total_ev == 100
