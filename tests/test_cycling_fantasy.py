import sys
import os
import ast
import pandas as pd
from unittest.mock import MagicMock, patch

# Mock dependencies before loading the code
mock_st = MagicMock()
sys.modules['streamlit'] = mock_st

file_path = os.path.join(os.path.dirname(__file__), '..', 'pages', 'Cycling_Fantasy', 'Classics', 'Dashboard.py')

with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

tree = ast.parse(code)
new_body = []
for node in tree.body:
    # Only keep imports and functions/classes to avoid running Streamlit UI code
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
        new_body.append(node)
tree.body = new_body

compiled = compile(tree, filename="<ast>", mode="exec")
namespace = {}
exec(compiled, namespace)

parse_pcs_pdf = namespace['parse_pcs_pdf']

def test_parse_pcs_pdf_success():
    mock_pdfplumber = MagicMock()
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    # Provide text that matches the regex: \d+\s+([A-Z\s]+)\s+([A-Z][a-z\s]+)
    # Example: 123 VAN AERT Wout 100
    mock_page.extract_text.return_value = "123 VAN AERT Wout 100\n45 POGACAR Tadej 50\nSome Random Text Without Numbers\n"
    mock_pdf.pages = [mock_page]
    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

    with patch.dict(sys.modules, {'pdfplumber': mock_pdfplumber}):
        riders = parse_pcs_pdf("dummy_file.pdf")

    assert isinstance(riders, list)
    assert len(riders) == 2
    assert "Wout VAN AERT" in riders
    assert "Tadej POGACAR" in riders

def test_parse_pcs_pdf_exception():
    mock_st.error.reset_mock()

    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.side_effect = Exception("Test PDF error")

    with patch.dict(sys.modules, {'pdfplumber': mock_pdfplumber}):
        riders = parse_pcs_pdf("dummy_file.pdf")

    assert isinstance(riders, list)
    assert len(riders) == 0
    mock_st.error.assert_called_once()
    assert "Error parsing PDF" in mock_st.error.call_args[0][0]
