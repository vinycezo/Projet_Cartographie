sql_ressources = [    
{"position": 100, "table": "$(vTable)", "source": "BSEG"},
{"position": 100, "table": "$(vTable)", "source": "KOLO"},
{"position": 250, "table": "$(vTable)", "source": "VBAK"},
{"position": 400, "table": "Clients", "source": "KNA1"}
]

new = {}
for value in sql_ressources :
    position = value['position']
    table = value['table']
    new.setdefault(position, {'table': table, 'sources':[]})
    new[position]['sources'].append(value['source'])

print(new)