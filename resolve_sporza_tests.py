import re

with open('tests/test_klassiekers_sporza.py', 'r') as f:
    content = f.read()

pattern1 = r"<<<<<<< HEAD\n        \n        # Define mock values for the module level variables that get populated during import\n        import pandas as pd\n        mock_df = pd.DataFrame\(\{'Naam': \['mock'\], 'Team': \['mock'\]\}\)\n        \n        # Provide a mock function to replace load_and_merge_data at import time\n        sporza.load_and_merge_data = MagicMock\(return_value=\(mock_df, \[\], \{\}\)\)\n        \n        try:\n            spec.loader.exec_module\(sporza\)"
replace1 = r"""        # Define mock values for the module level variables that get populated during import
        import pandas as pd
        mock_df = pd.DataFrame({'Naam': ['mock'], 'Team': ['mock']})

        # Provide a mock function to replace load_and_merge_data at import time
        sporza.load_and_merge_data = MagicMock(return_value=(mock_df, [], {}))

        try:
            spec.loader.exec_module(sporza)"""
content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)

pattern2 = r"<<<<<<< HEAD\n    assert bepaal_klassieker_type\(\{'SPR': '90', 'COB': '80', 'HLL': '70'\}\) == 'Sprint'\n    assert bepaal_klassieker_type\(\{'SPR': '70', 'COB': '90', 'HLL': '80'\}\) == 'Kassei'\n    assert bepaal_klassieker_type\(\{'SPR': '70', 'COB': '80', 'HLL': '90'\}\) == 'Heuvel'\n=======\n    assert bepaal_klassieker_type\(\{'SPR': 90, 'COB': 80, 'HLL': 70\}\) == 'Sprint'\n    assert bepaal_klassieker_type\(\{'SPR': 70, 'COB': 90, 'HLL': 80\}\) == 'Kassei'\n    assert bepaal_klassieker_type\(\{'SPR': 70, 'COB': 80, 'HLL': 90\}\) == 'Heuvel'\n>>>>>>> origin/main"
replace2 = r"""    assert bepaal_klassieker_type({'SPR': '90', 'COB': '80', 'HLL': '70'}) == 'Sprint'
    assert bepaal_klassieker_type({'SPR': '70', 'COB': '90', 'HLL': '80'}) == 'Kassei'
    assert bepaal_klassieker_type({'SPR': '70', 'COB': '80', 'HLL': '90'}) == 'Heuvel'"""
content = re.sub(pattern2, replace2, content, flags=re.MULTILINE)

with open('tests/test_klassiekers_sporza.py', 'w') as f:
    f.write(content)
