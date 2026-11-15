from variable_resolver import VariableResolver
from qlik_script_extractor import QlikScriptExtractor
from pprint import pprint
from pathlib import Path 

script = Path("/home/nkrou/python/exemple_commun_extract_anonymisé.txt").read_text(
    encoding="utf-8-sig"
)


# script = """
# SET vChemin_extract='lib://Prod/Ppl/Commun/02_qvd/01_extract';

# BSEG:
# LOAD MANDT, BUKRS;
# SELECT MANDT, BUKRS FROM BSEG;

# STORE BSEG INTO [$(vChemin_extract)/BSEG.qvd](qvd);

# LOAD *;
# SELECT * FROM VBAP;

# VENTES:
# LOAD *;
# SELECT * FROM VBAK;

# LISTE_TABLE_CLAUSE_WHERE:
# LOAD *
# FROM [lib://Prod/Ppl/Table.xlsx]
# (ooxml, embedded labels, table is TABLE);
# """

resolver = VariableResolver()
resolver.extract_set_variables(script)

extractor = QlikScriptExtractor(resolver)

# print("SOURCES SQL")
# for source in extractor.extract_sql_sources(script):
#     print(source)

# print("\nSOURCES FICHIERS")
# for source in extractor.extract_file_sources(script):
#     print(source)

inventory = extractor.build_table_inventory(script)


for table_name, details in inventory.items():
    print(f"\nTABLE : {table_name}")
    pprint(details)
