import re

with open('tests/test_klassiekers_sporza.py', 'r') as f:
    content = f.read()

pattern1 = r"        try:\n            spec\.loader\.exec_module\(sporza\)\n        except Exception as e:\n            print\(f\"Exception during module exec: \{e\}\"\)\n            pass\n            \n=======\n\n        # We need to catch exceptions or mock out more data if this fails\n        try:\n            # mock get_file_mod_time and load_and_merge_data directly in the module namespace before executing\n            sporza\.get_file_mod_time = lambda x: 0\n            sporza\.load_and_merge_data = lambda x, y: \(None, \[\], \{\}\)\n            spec\.loader\.exec_module\(sporza\)\n        except ValueError:\n            pass # Ignore unpacking error on load_and_merge_data at module level\n>>>>>>> origin/main"
replace1 = r"""        try:
            spec.loader.exec_module(sporza)
        except Exception as e:
            print(f"Exception during module exec: {e}")
            pass"""

content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)

with open('tests/test_klassiekers_sporza.py', 'w') as f:
    f.write(content)
