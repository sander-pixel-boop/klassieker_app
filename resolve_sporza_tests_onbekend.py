import re

with open('tests/test_klassiekers_sporza.py', 'r') as f:
    content = f.read()

pattern1 = r"    assert bepaal_klassieker_type\(\{\}\) == 'Onbekend'"
replace1 = r"    assert bepaal_klassieker_type({}) is None"
content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)

pattern2 = r"    assert bepaal_klassieker_type\(\{'SPR': 'a', 'COB': 'b', 'HLL': 'c'\}\) == 'Onbekend'"
replace2 = r"    assert bepaal_klassieker_type({'SPR': 'a', 'COB': 'b', 'HLL': 'c'}) is None"
content = re.sub(pattern2, replace2, content, flags=re.MULTILINE)

with open('tests/test_klassiekers_sporza.py', 'w') as f:
    f.write(content)
