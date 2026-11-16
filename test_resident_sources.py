import unittest

from qlik_script_extractor import QlikScriptExtractor
from variable_resolver import VariableResolver


class ResidentSourceTests(unittest.TestCase):
    def inventory(self, script):
        return QlikScriptExtractor(VariableResolver()).build_table_inventory(script)

    def test_dynamic_sql_preceding_load_and_resident(self):
        for separator in ('', ';'):
            with self.subTest(separator=separator):
                inventory = self.inventory("""
SET vChemin_extract = 'DATABASE';
SET vTable = 'abcd';
temp_$(vTable):
LOAD c""" + separator + """
SQL SELECT c
FROM $(vChemin_extract).SOCIETES;
$(vTable):
LOAD*
Resident temp_$(vTable);
STORE $(vTable) INTO [lib://Output/$(vTable).qvd](qvd);
""")
                expected = [{'type': 'SQL', 'name': 'DATABASE.SOCIETES', 'where': None}]
                self.assertEqual(set(inventory), {'temp_abcd', 'abcd'})
                self.assertEqual(inventory['temp_abcd']['sources'], expected)
                self.assertEqual(inventory['abcd']['sources'], expected)
                self.assertEqual(inventory['abcd']['outputs'], ['lib://Output/abcd.qvd'])

    def test_resident_chain_and_variable_reassignment(self):
        inventory = self.inventory("""
SET vTable='First';
temp_$(vTable):
LOAD *;
SELECT * FROM FIRST_SOURCE WHERE active = 1;
$(vTable): LOAD * RESIDENT temp_$(vTable);
SET vTable='Second';
temp_$(vTable):
LOAD * FROM [lib://Input/second.qvd](qvd);
$(vTable): LOAD * RESIDENT temp_$(vTable);
[Final table]: LOAD * RESIDENT [Second];
// Ignored: LOAD * RESIDENT First;
EXIT SCRIPT;
AfterExit: LOAD * RESIDENT First;
""")
        self.assertEqual(inventory['First']['sources'], [
            {'type': 'SQL', 'name': 'FIRST_SOURCE', 'where': 'active = 1'}])
        self.assertEqual(inventory['Second']['sources'], [
            {'type': 'FILE', 'name': 'lib://Input/second.qvd', 'where': None}])
        self.assertEqual(inventory['Final table']['sources'], inventory['Second']['sources'])
        self.assertNotIn('Ignored', inventory)
        self.assertNotIn('AfterExit', inventory)


if __name__ == '__main__':
    unittest.main()
