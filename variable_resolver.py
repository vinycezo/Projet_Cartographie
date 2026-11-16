
import re


class VariableResolver:

    def __init__(self):
        self.variables = {}
        self.variables_history = {}

    def extract_set_variables(self, script: str):
        """
        Extrait SET et les LET dont la valeur est une chaîne littérale.
        Les autres LET masquent toute valeur statique précédente.
        Exemple :
        SET vChemin_extract='lib://Prod/Ppl/Commun';
        """
        self.variables_history = {}

        # Supprime les commentaires de ligne entière
        script = re.sub(
            r"(?m)^\s*//[^\n]*$",
            lambda match: re.sub(r"[^\r\n]", " ", match.group()),
            script
        )

        pattern = (
            r"(?im)^\s*(SET|LET)\s+([A-Za-z_]\w*)\s*=\s*"
            r"((?:'[^']*(?:''[^']*)*'|\"[^\"]*\"|[^;'\"\r\n])*);"
        )

        for match in re.finditer(pattern, script):
            assignment = match.group(1).upper()
            name = match.group(2)
            value = match.group(3).strip()

            if assignment == "LET":
                # Pas d'évaluation d'expressions Qlik arbitraires.
                if re.fullmatch(r"'(?:[^']|'')*'", value):
                    value = value[1:-1].replace("''", "'")
                else:
                    value = None
            elif len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]

            self.variables_history.setdefault(name, []).append({
                "position":match.start(),
                "value":value
            })

        return self.variables_history

    def get_variable_at(self, name, position):
        history = self.variables_history.get(name, [])

        valid_values = [item for item in history if item['position'] < position]

        if not valid_values:
            return None

        return valid_values[-1]["value"]

     

    def resolve(self, expression: str, position: int):
        """
        Remplace les références $(variable)
        par leur valeur connue.
        """

        pattern = r"\$\(([A-Za-z_]\w*)\)"

        def replace_variable(match):
            name = match.group(1)

            value = self.get_variable_at(name, position)

            if value is None:
                return match.group(0)

            return value

        result = expression

        # Autorise les variables qui référencent d'autres variables
        for _ in range(10):
            resolved = re.sub(pattern, replace_variable, result)

            if resolved == result:
                break

            result = resolved

        return result


# script = """
# SET vSource='SDP';
# SET vChemin_extract='lib://Prod/Ppl/Commun/02_qvd/01_extract';

# // SET vAncienChemin='lib://Ancien/Dossier';
# """

# resolver = VariableResolver()

# variables = resolver.extract_set_variables(script)

# print(variables)

# path = resolver.resolve(
#     "$(vChemin_extract)/BSEG.qvd"
# )

# print(path)
