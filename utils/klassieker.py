def bepaal_klassieker_type(row):
    try:
        cob = int(row.get('COB', 0))
        hll = int(row.get('HLL', 0))
        spr = int(row.get('SPR', 0))
        mtn = int(row.get('MTN', 0))
        itt = int(row.get('ITT', 0))
        gc = int(row.get('GC', 0))
    except (ValueError, TypeError):
        return 'Onbekend'

    elite = []
    if cob >= 85: elite.append('Kassei')
    if hll >= 85: elite.append('Heuvel')
    if spr >= 85: elite.append('Sprint')

    if len(elite) == 3: return 'Allround / Multispecialist'
    elif len(elite) == 2: return ' / '.join(elite)
    elif len(elite) == 1: return elite[0]
    else:
        s = {'Kassei': cob, 'Heuvel': hll, 'Sprint': spr, 'Klimmer': mtn, 'Tijdrit': itt, 'Klassement': gc}
        if sum(s.values()) == 0: return 'Onbekend'
        return max(s, key=s.get)
