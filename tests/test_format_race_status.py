import pytest
import pandas as pd
import numpy as np
import ast
import os

with open("pages/Klassiekers - Scorito.py", "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)

# Find the format_race_status function
func_ast = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "format_race_status":
        func_ast = ast.Module(body=[node], type_ignores=[])
        break

if not func_ast:
    raise ValueError("Function 'format_race_status' not found in pages/Klassiekers - Scorito.py")

namespace = {"pd": pd, "np": np}
exec(compile(func_ast, filename="<ast>", mode="exec"), namespace)
format_race_status = namespace["format_race_status"]


class TestFormatRaceStatus:
    def test_special_codes(self):
        """Test the special numeric codes (999, 998, 997, 996)."""
        limit = 20
        assert format_race_status(999, limit) == ""
        assert format_race_status(998, limit) == "✅"
        assert format_race_status(997, limit) == "❌"
        assert format_race_status(996, limit) == "DNF"

    def test_within_limit(self):
        """Test when the value is less than or equal to the limit."""
        assert format_race_status(1, 20) == "**1**"
        assert format_race_status(20, 20) == "**20**"

        # String representations of numbers
        assert format_race_status("10", 20) == "**10**"

    def test_above_limit_but_not_special(self):
        """Test when the value is greater than the limit, but not a special code."""
        assert format_race_status(21, 20) == "21"
        assert format_race_status(100, 20) == "100"
        assert format_race_status("50", 20) == "50"

        # Test with a different limit
        assert format_race_status(11, 10) == "11"

    def test_na_values(self):
        """Test handling of NaN/NA/None values."""
        limit = 20
        assert format_race_status(np.nan, limit) == ""
        assert format_race_status(pd.NA, limit) == ""
        assert format_race_status(None, limit) == ""
        assert format_race_status("", limit) == ""

    def test_unparseable_strings(self):
        """Test handling of strings that cannot be parsed as float/int."""
        limit = 20
        assert format_race_status("DNS", limit) == "DNS"
        assert format_race_status("DNF", limit) == "DNF"
        assert format_race_status("OOT", limit) == "OOT"
        assert format_race_status("Some random string", limit) == "Some random string"
