
import re


class QlikScriptExtractor:

    def __init__(self, resolver):
        self.resolver = resolver

    @staticmethod
    def clean_script(script: str):
         """Supprime les commentaires de ligne et les commentaires // en fin de ligne."""
         return re.sub(r"(?m)^\s*//[^\n]*$", "", script)
    # def clean_script(script: str):
    #     """Supprime les commentaires // en préservant chaînes et chemins entre crochets."""
    #     pattern = r"'[^']*(?:''[^']*)*'|\"[^\"]*(?:\"\"[^\"]*)*\"|\[[^\]]*\]|//[^\r\n]*"
    #     return re.sub(
    #         pattern,
    #         lambda match: "" if match.group(0).startswith("//") else match.group(0),
    #         script,
    #     )



    def extract_stores(self, script: str):
        stores = []


        pattern = (
            r"\bSTORE\s+"
            r"(\[[^\]]+\]|[^\s;]+)"
            r"\s+INTO\s+"
            r"\[([^\]]+)\]"
            r"\s*(?:\([^)]*\))?\s*;"
        )

        for match in re.finditer(
            pattern, script, flags=re.IGNORECASE
        ):
            raw_table = match.group(1).strip("[]")
            raw_path = match.group(2)

            table_name = self.resolver.resolve(raw_table, match.start())
            resolved_path = self.resolver.resolve(raw_path, match.start())

            stores.append({
                "table": table_name,
                "output_file": resolved_path
            })

        return stores

    def get_executable_script(self, script):
        script = self.clean_script(script)

        match = re.search(
            r"(?im)^\s*EXIT\s+SCRIPT\s*;",
            script
        )

        if match:
            return script[:match.start()]
        return script

    def extract_sql_sources(self, script: str):
        sources = []

        pattern = (
            r"(?im)^\s*"
            r"(?:(\[[^\]]+\]|[A-Za-z_]\w*)\s*:\s*)?"
            r"LOAD\b[^;]*;\s*"
            r"SELECT\b(.*?);"
        )

        for match in re.finditer(pattern, script, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1)
            sql_query = match.group(2)

            sql_tables = re.findall(
                r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w.~]*)",
                sql_query,
                flags=re.IGNORECASE
            )

            if table_name:
                table_name = self.resolver.resolve(table_name.strip("[]"), match.start())
            elif sql_tables:
                table_name = self.resolver.resolve(sql_tables[0], match.start())    

            for source in sql_tables:
                sources.append({
                    "table": table_name,
                    "source_type": "SQL",
                    "source": self.resolver.resolve(source, match.start())
                })

        return sources

    def extract_file_sources(self, script: str):
        sources = []

        pattern = (
            r"(?im)^\s*"
            r"(?:(\$\([A-Za-z_]\w*\)|\[[^\]]+\]|[A-Za-z_]\w*)\s*:\s*)?"
            r"LOAD\b[^;]*?\bFROM\s+"
            r"(?:\[([^\]]+)\]|([^\s;()]+(?:\$\([A-Za-z_]\w*\)[^\s;()]*)*))"
        )

        for match in re.finditer(pattern, script, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1)
            raw_path = match.group(2) or match.group(3)

            if table_name:
                table_name = self.resolver.resolve(table_name.strip("[]"), match.start())

            sources.append({
                "table": table_name,
                "source_type": "FILE",
                "source": self.resolver.resolve(raw_path,match.start())
            })

        return sources


    def build_table_inventory(self, script):
        inventory = {}
        #script = self.clean_script(script)
        script = self.get_executable_script(script)

        self.resolver.extract_set_variables(script)

        sql_sources = self.extract_sql_sources(script)
        file_sources = self.extract_file_sources(script)
        stores = self.extract_stores(script)

        # 1. Ajouter les sources
        for source in sql_sources + file_sources:

            table_name = source["table"]

            inventory.setdefault(
                table_name,
                {"sources": [], "outputs": []}
            )
            source_info = {
                "type": source["source_type"],
                "name": source["source"]
            }

            if source_info not in inventory[table_name]["sources"]:
                inventory[table_name]["sources"].append(source_info)

        # 2. Ajouter les fichiers de sortie
        for store in stores:

            table_name = store["table"]

            inventory.setdefault(
                table_name,
                {"sources": [], "outputs": []}
            )

            inventory[table_name]["outputs"].append(
                store["output_file"]
            )

        return inventory

        
