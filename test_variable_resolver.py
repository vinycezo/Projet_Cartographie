import unittest

from qlik_script_extractor import QlikScriptExtractor
from variable_resolver import VariableResolver


class StaticLetTests(unittest.TestCase):
    def test_literal_let_is_used_in_file_source(self):
        inventory = QlikScriptExtractor(VariableResolver()).build_table_inventory("""
let vConnection = 'loml';
request:
LOAD bibi, Cici
FROM $(vConnection);
""")
        self.assertEqual(inventory['request']['sources'], [
            {'type': 'FILE', 'name': 'loml', 'where': None}])

    def test_only_whole_string_literals_are_static(self):
        resolver = VariableResolver()
        script = """
LET escaped = 'l''ami;source';
LET combined = 'a' & 'b';
LET dynamic = TableName(i);
"""
        resolver.extract_set_variables(script)
        self.assertEqual(resolver.resolve('$(escaped)', len(script)), "l'ami;source")
        self.assertEqual(resolver.resolve('$(combined)', len(script)), '$(combined)')
        self.assertEqual(resolver.resolve('$(dynamic)', len(script)), '$(dynamic)')

    def test_dynamic_reassignment_invalidates_previous_value(self):
        resolver = VariableResolver()
        script = """
SET vTable = 'original';
TRACE before;
LET vTable = 'static';
TRACE middle;
LET vTable = TableName(i);
TRACE after;
"""
        resolver.extract_set_variables(script)
        for marker, expected in [('before', 'original'), ('middle', 'static'), ('after', '$(vTable)')]:
            self.assertEqual(resolver.resolve('$(vTable)', script.index(marker)), expected)


if __name__ == '__main__':
    unittest.main()
