import unittest

from qlik_script_extractor import QlikScriptExtractor
from variable_resolver import VariableResolver


class WhereExtractionTests(unittest.TestCase):
    def setUp(self):
        self.extractor = QlikScriptExtractor(VariableResolver())

    def test_sql_conditions_and_distinct_reads(self):
        inventory = self.extractor.build_table_inventory("""
SET vYear='2024';
Sales:
LOAD *;
SELECT * FROM SALES WHERE year >= '$(vYear)'
AND status = 'where; active' // ignore this
ORDER BY year;
Sales:
LOAD *;
SELECT * FROM SALES WHERE status = 'closed';
LOAD *;
SELECT * FROM OTHER;
""")
        sources = inventory['Sales']['sources']
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]['where'], "year >= '2024'\nAND status = 'where; active'")
        self.assertEqual(sources[1]['where'], "status = 'closed'")
        self.assertIsNone(inventory['OTHER']['sources'][0]['where'])

    def test_file_filter_and_dynamic_sql(self):
        inventory = self.extractor.build_table_inventory("""
Tables:
LOAD * FROM [lib://Prod/Table.xlsx]
(ooxml, embedded labels, table is TABLE)
where not isnull(Clause_Where)
and Manuel <> 'Oui';
$(vNom_Table):
LOAD *;
SELECT * FROM $(vNom_Table) where $(vClause_where);
""")
        source = inventory['Tables']['sources'][0]
        self.assertEqual(source['name'], 'lib://Prod/Table.xlsx')
        self.assertEqual(source['where'], "not isnull(Clause_Where)\nand Manuel <> 'Oui'")
        self.assertEqual(inventory['$(vNom_Table)']['sources'][0]['where'], '$(vClause_where)')

    def test_comments_literals_subqueries_and_exit(self):
        inventory = self.extractor.build_table_inventory("""
LOAD *;
SELECT 'where' FROM ITEMS
WHERE id IN (SELECT id FROM OTHER WHERE active = 1)
/* excluded */ AND url = 'https://example.org';
exit script;
LOAD *;
SELECT * FROM IGNORED WHERE x = 1;
""")
        self.assertEqual(set(inventory), {'ITEMS'})
        condition = inventory['ITEMS']['sources'][0]['where']
        self.assertIn('WHERE active = 1)', condition)
        self.assertIn("'https://example.org'", condition)
        self.assertNotIn('excluded', condition)


if __name__ == '__main__':
    unittest.main()
