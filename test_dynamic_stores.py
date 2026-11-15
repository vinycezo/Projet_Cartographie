import unittest

from qlik_script_extractor import QlikScriptExtractor
from variable_resolver import VariableResolver


class DynamicStoreTests(unittest.TestCase):
    def test_global_store_fills_missing_outputs(self):
        for exit_statement in ('', 'exit script;'):
            with self.subTest(exit_statement=exit_statement):
                script = """
SET vPath='lib://Output';
Explicit:
LOAD *;
SELECT * FROM FIRST;
STORE Explicit INTO [lib://Special/Explicit.qvd](qvd);
Missing:
LOAD *;
SELECT * FROM SECOND;
""" + exit_statement + r"""
// for i=0 to NoOfTables()-1
// let d=TableName(i);
// store $(d) into [wrong/$(d).qvd](qvd);
// next
for i=0 to NoOfTables()-1
    let d=TableName(i);
    store $(d) into [$(vPath)\$(d).qvd](qvd);
next
"""
                inventory = QlikScriptExtractor(VariableResolver()).build_table_inventory(script)
                self.assertEqual(set(inventory), {'Explicit', 'Missing'})
                self.assertEqual(inventory['Explicit']['outputs'], ['lib://Special/Explicit.qvd'])
                self.assertEqual(inventory['Missing']['outputs'], [r'lib://Output\Missing.qvd'])


if __name__ == '__main__':
    unittest.main()
