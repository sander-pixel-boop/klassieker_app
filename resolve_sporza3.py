import re

with open('pages/Klassiekers - Sporza.py', 'r') as f:
    content = f.read()

pattern1 = r">>>>>>> origin/main\n            \n                penalties"
replace1 = r"""        t_moments = sorted(t_moments, key=lambda x: available_races.index(x))
                penalties"""

content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)

pattern2 = r"            new_col\.append\(get_numeric_status\(is_on_list, is_on_list, is_verreden, rank_str\)\)\n        d_df\[c\] = pd\.to_numeric\(new_col\)\n>>>>>>> origin/main"
replace2 = ""

content = re.sub(pattern2, replace2, content, flags=re.MULTILINE)

with open('pages/Klassiekers - Sporza.py', 'w') as f:
    f.write(content)
