
import re


class QlikScriptExtractor:

    # Les expansions peuvent faire partie d'un nom : temp_$(vTable).
    IDENTIFIER = r'(?:\[[^\]]+\]|(?:\$\([A-Za-z_]\w*\)|[A-Za-z_])(?:\$\([A-Za-z_]\w*\)|[\w.~])*)'

    def __init__(self, resolver):
        self.resolver = resolver

    @staticmethod
    def clean_script(script: str):
        """Masque les commentaires en préservant les chaînes et les positions."""
        pattern = r"'[^'\r\n]*(?:''[^'\r\n]*)*'|\"[^\"\r\n]*(?:\"\"[^\"\r\n]*)*\"|\[[^\]\r\n]*\]|//[^\r\n]*|/\*[\s\S]*?\*/"
        return re.sub(
            pattern,
            lambda m: re.sub(r"[^\r\n]", " ", m.group())
            if m.group().startswith(("//", "/*")) else m.group(),
            script,
        )

    @staticmethod
    def extract_where(statement: str):
        """Renvoie la condition WHERE externe, sans les clauses SQL suivantes."""
        tokens = r"'[^']*(?:''[^']*)*'|\"[^\"]*(?:\"\"[^\"]*)*\"|\[[^\]]*\]|\(|\)|\bWHERE\b|\b(?:GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|UNION)\b"
        depth = 0
        start = None
        for match in re.finditer(tokens, statement, re.IGNORECASE):
            token = match.group()
            if token == "(":
                depth += 1
            elif token == ")":
                depth -= 1
            elif depth == 0 and token.upper() == "WHERE" and start is None:
                start = match.end()
            elif depth == 0 and start is not None and token[0] not in "'\"[":
                return statement[start:match.start()].strip()
        return statement[start:].strip() if start is not None else None
    # def clean_script(script: str):
    #     """Supprime les commentaires // en préservant chaînes et chemins entre crochets."""
    #     pattern = r"'[^']*(?:''[^']*)*'|\"[^\"]*(?:\"\"[^\"]*)*\"|\[[^\]]*\]|//[^\r\n]*"
    #     return re.sub(
    #         pattern,
    #         lambda match: "" if match.group(0).startswith("//") else match.group(0),
    #         script,
    #     )



    def _path_variables(self, expression, position, excluded=()):
        variables = []
        names = dict.fromkeys(re.findall(r"\$\(([A-Za-z_]\w*)\)", expression))
        for name in names:
            if name in excluded:
                continue
            value = self.resolver.get_variable_at(name, position)
            if value is not None:
                value = self.resolver.resolve(value, position)
            variables.append((name, value))
        return tuple(variables)

    def extract_stores(self, script: str, *, include_variables=False):
        stores = []


        pattern = (
            r"\bSTORE\s+"
            r"(?:[^;]+?\s+FROM\s+)?(\[[^\]]+\]|[^\s;]+)"
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
            if include_variables:
                table_variables = re.findall(r"\$\(([A-Za-z_]\w*)\)", raw_table)
                stores[-1]["variables"] = self._path_variables(raw_path, match.start(), table_variables)

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

    def extract_sql_sources(self, script: str, *, include_variables=False):
        script = self.clean_script(script)
        sources = []

        pattern = (
            r"(?im)^\s*"
            rf"(?:({self.IDENTIFIER})\s*:\s*)?"
            r"LOAD\b(?:'[^']*(?:''[^']*)*'|\"[^\"]*\"|[^;'\"])*?;?\s*"
            r"(?:SQL\s+)?SELECT\b((?:'[^']*(?:''[^']*)*'|\"[^\"]*\"|[^;'\"])*);"
        )

        connections = iter(re.finditer(
            r"(?im)^[^\S\r\n]*(?:LIB\s+)?CONNECT\s+TO\s+([^;]+);", script
        ))
        next_connection = next(connections, None) if include_variables else None
        connection_variables = ()
        for match in re.finditer(pattern, script, re.IGNORECASE | re.DOTALL):
            raw_table = match.group(1)
            table_name = raw_table
            sql_query = match.group(2)

            sql_tables = re.findall(
                rf"\b(?:FROM|JOIN)\s+({self.IDENTIFIER})",
                sql_query,
                flags=re.IGNORECASE
            )

            if table_name:
                table_name = self.resolver.resolve(table_name.strip("[]"), match.start())
            elif sql_tables:
                table_name = self.resolver.resolve(sql_tables[0], match.start())    

            while next_connection is not None and next_connection.start() < match.start():
                connection_variables = self._path_variables(next_connection.group(1), next_connection.start())
                next_connection = next(connections, None)

            for source in sql_tables:
                sources.append({
                    "table": table_name,
                    "source_type": "SQL",
                    "source": self.resolver.resolve(source, match.start()),
                    "where": self._resolve_where(sql_query, match.start()),
                })
                if include_variables:
                    table_variables = re.findall(r"\$\(([A-Za-z_]\w*)\)", raw_table or "")
                    variables = connection_variables + self._path_variables(
                        source, match.start(), table_variables
                    )
                    sources[-1]["variables"] = tuple(dict.fromkeys(variables))

        return sources

    def extract_file_sources(self, script: str, *, include_variables=False):
        script = self.clean_script(script)
        sources = []

        pattern = (
            r"(?im)^\s*"
            rf"(?:({self.IDENTIFIER})\s*:\s*)?"
            r"LOAD\b(?:'[^']*(?:''[^']*)*'|\"[^\"]*\"|(?!(?:SQL\s+)?SELECT\b)[^;'\"])*?\bFROM\s+"
            r"(?:\[([^\]]+)\]|((?:\$\([A-Za-z_]\w*\)|[^\s;()])+))"
            r"((?:'[^']*(?:''[^']*)*'|\"[^\"]*\"|[^;'\"])*);"
        )

        for match in re.finditer(pattern, script, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1)
            raw_path = match.group(2) or match.group(3)

            if table_name:
                table_name = self.resolver.resolve(table_name.strip("[]"), match.start())

            sources.append({
                "table": table_name,
                "source_type": "FILE",
                "source": self.resolver.resolve(raw_path,match.start()),
                "where": self._resolve_where(match.group(4), match.start()),
            })
            if include_variables:
                sources[-1]["variables"] = self._path_variables(raw_path, match.start())

        return sources

    def _resolve_where(self, statement, position):
        condition = self.extract_where(statement)
        return self.resolver.resolve(condition, position) if condition is not None else None

    def extract_resident_sources(self, script):
        """Extrait les liens entre tables chargées avec RESIDENT."""
        pattern = (
            rf"(?im)^\s*({self.IDENTIFIER})\s*:\s*LOAD\b"
            r"(?:'[^']*(?:''[^']*)*'|\"[^\"]*\"|[^;'\"])*?"
            rf"\bRESIDENT\s+({self.IDENTIFIER})"
            r"((?:'[^']*(?:''[^']*)*'|\"[^\"]*\"|[^;'\"])*);"
        )
        links = []
        for match in re.finditer(pattern, self.clean_script(script), re.IGNORECASE):
            links.append({
                "table": self.resolver.resolve(match.group(1).strip("[]"), match.start()),
                "resident": self.resolver.resolve(match.group(2).strip("[]"), match.start()),
            })
        return links

    def extract_dynamic_store_templates(self, script):
        """Repère les boucles FOR / TableName / STORE de toutes les tables."""
        templates = []
        pattern = (
            r"\bFOR\s+\w+\s*=\s*0\s+TO\s+NoOfTables\(\)\s*-\s*1"
            r"(?P<body>.*?)\bNEXT\b"
        )
        for loop in re.finditer(pattern, script, re.IGNORECASE | re.DOTALL):
            body = loop.group('body')
            assignment = re.search(
                r"\bLET\s+(\w+)\s*=\s*TableName\([^)]*\)\s*;",
                body, re.IGNORECASE,
            )
            if not assignment:
                continue
            table_variable = '$(' + assignment.group(1) + ')'
            store = re.search(
                r"\bSTORE\s+" + re.escape(table_variable)
                + r"\s+INTO\s+\[([^\]]+)\]\s*(?:\([^)]*\))?\s*;",
                body, re.IGNORECASE,
            )
            if store:
                templates.append({
                    'variable': table_variable,
                    'path': store.group(1),
                    'position': loop.start('body') + store.start(),
                })
        return templates

    def build_table_inventory(self, script, *, include_variables=False):
        inventory = {}
        # Le STORE global sert de modèle de sortie, même après EXIT SCRIPT.
        full_script = self.clean_script(script)
        templates = self.extract_dynamic_store_templates(full_script)
        script = self.get_executable_script(script)

        self.resolver.extract_set_variables(script)

        sql_sources = self.extract_sql_sources(script, include_variables=include_variables)
        file_sources = self.extract_file_sources(script, include_variables=include_variables)
        stores = self.extract_stores(script, include_variables=include_variables)

        # 1. Ajouter les sources
        for source in sql_sources + file_sources:

            table_name = source["table"]

            inventory.setdefault(
                table_name,
                {"sources": [], "outputs": []}
            )
            source_info = {
                "type": source["source_type"],
                "name": source["source"],
                "where": source["where"],
            }
            if include_variables:
                source_info["variables"] = source["variables"]

            if source_info not in inventory[table_name]["sources"]:
                inventory[table_name]["sources"].append(source_info)

        # Propager les sources physiques à travers les chargements RESIDENT.
        for link in self.extract_resident_sources(script):
            details = inventory.setdefault(link['table'], {"sources": [], "outputs": []})
            upstream = inventory.get(link['resident'], {}).get('sources', [])
            for source in list(upstream):
                if source not in details['sources']:
                    details['sources'].append(source.copy())

        # 2. Ajouter les fichiers de sortie
        for store in stores:

            table_name = store["table"]
            if any(table_name == template['variable'] for template in templates):
                continue

            inventory.setdefault(
                table_name,
                {"sources": [], "outputs": []}
            )

            inventory[table_name]["outputs"].append(
                store["output_file"]
            )
            if include_variables:
                inventory[table_name].setdefault("output_variables", []).extend(store["variables"])

        # 3. Compléter uniquement les tables sans sortie explicite.
        for table_name, details in inventory.items():
            if table_name is None or details['outputs']:
                continue
            for template in templates:
                path = template['path'].replace(template['variable'], table_name)
                if include_variables:
                    variables = self._path_variables(
                        template["path"], template["position"], (template["variable"][2:-1],)
                    )
                    details.setdefault("output_variables", []).extend(variables)
                path = self.resolver.resolve(path, template['position'])
                if path not in details['outputs']:
                    details['outputs'].append(path)

        return inventory

        
