import re

with open('pages/Klassiekers - Sporza.py', 'r') as f:
    content = f.read()

pattern1 = r"<<<<<<< HEAD\n            st\.divider\(\)\n            st\.title\(\"🚴 Sporza AI Coach\"\)\n            ev_method = st\.selectbox\(\"🧮 Rekenmodel \(EV\)\", \[\"1\. Sporza Ranking \(Dynamisch\)\", \"2\. Originele Curve \(Macht 4\)\"\]\)\n            toon_uitslagen = st\.checkbox\(\"🏁 Koersen zijn begonnen \(Toon uitslagen\)\", value=True\)\n        \n            st\.divider\(\)\n            st\.markdown\(\"### 🔁 Transfer Strategie\"\)\n            num_transfers = st\.slider\(\"Aantal geplande transfers\", 0, 5, 0\)\n        \n            t_moments = \[\]\n            if num_transfers > 0:\n                st\.write\(\"Wanneer wil je de wissels inzetten\?\"\)\n                for i in range\(num_transfers\):\n                    default_idx = min\(len\(available_races\)-2, 13\)\n                    moment = st\.selectbox\(f\"Wissel \{i\+1\} ná:\", options=available_races\[:-1\], index=default_idx, key=f\"t_\{i\}\"\)\n                    t_moments\.append\(moment\)\n                \n                t_moments = sorted\(t_moments, key=lambda x: available_races\.index\(x\)\)\n=======\n"
replace1 = ""
content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)

pattern2 = r"<<<<<<< HEAD\n                new_col\.append\(get_numeric_status\(is_on_list, is_on_list, is_verreden, rank_str\)\)\n            d_df\[c\] = pd\.to_numeric\(new_col\)\n=======\n"
replace2 = ""
content = re.sub(pattern2, replace2, content, flags=re.MULTILINE)

with open('pages/Klassiekers - Sporza.py', 'w') as f:
    f.write(content)
