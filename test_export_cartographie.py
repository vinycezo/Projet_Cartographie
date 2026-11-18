import unittest
from pathlib import Path

from export_cartographie import application_rows, table_rows
from qlik_script_extractor import QlikScriptExtractor
from variable_resolver import VariableResolver


class ExportRowsTests(unittest.TestCase):
    def test_sql_file_and_resident_rows(self):
        script = r"""
SET vChemin_extract='lib://Output';
SET vSource='lib://Input';
SET vResidentName='Final';
SET vSqlTable='ZBI_STAT_REAP';
ZBI_STAT_REAP:
SQL SELECT * FROM $(vSqlTable) WHERE ERDAT >= '$(vDateminimum)';
Final:
LOAD * RESIDENT ZBI_STAT_REAP;
STORE Final INTO [$(vChemin_extract)\$(vResidentName).qvd](qvd);
LISTE_TABLE_SANS_CLAUSE_WHERE:
LOAD * FROM [lib://Prod/ppl/Table.xlsx] (ooxml)
WHERE isnull(Clause_Where);
STORE LISTE_TABLE_SANS_CLAUSE_WHERE INTO
[$(vChemin_extract)\LISTE_TABLE_SANS_CLAUSE_WHERE.qvd](qvd);
VariableFile:
LOAD * FROM [$(vSource)/data.qvd] (qvd);
STORE VariableFile INTO [$(vChemin_extract)/VariableFile.qvd](qvd);
"""
        inventory = QlikScriptExtractor(VariableResolver()).build_table_inventory(
            script, include_variables=True,
        )
        self.assertEqual(list(application_rows(Path("Extract.qvs"), inventory)), [
            ("Extract", "vSource", "lib://Input", "vChemin_extract", "lib://Output"),
        ])
        self.assertCountEqual(list(table_rows("Extract", inventory)), [
            ("Extract", "ZBI_STAT_REAP", "ZBI_STAT_REAP", None,
             "ERDAT >= '$(vDateminimum)'", None),
            ("Extract", "ZBI_STAT_REAP", "Final", None, "ERDAT >= '$(vDateminimum)'",
             "vChemin_extract"),
            ("Extract", None, "LISTE_TABLE_SANS_CLAUSE_WHERE", "lib://Prod/ppl/Table.xlsx",
             "isnull(Clause_Where)", "vChemin_extract"),
            ("Extract", None, "VariableFile", "vSource", None, "vChemin_extract"),
        ])
