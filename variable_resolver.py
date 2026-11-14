
import re


class VariableResolver:

    def __init__(self):
        self.variables = {}

    def extract_set_variables(self, script: str):
        """
        Extrait les variables définies avec SET.
        Exemple :
        SET vChemin_extract='lib://Prod/Ppl/Commun';
        """

        # Supprime les commentaires de ligne entière
        script = re.sub(
            r"(?m)^\s*//[^\n]*$",
            "",
            script
        )

        pattern = r"(?im)^\s*SET\s+([A-Za-z_]\w*)\s*=\s*([^\r\n;]*);"

        for match in re.finditer(pattern, script):
            name = match.group(1)
            value = match.group(2).strip()

            # Retirer les guillemets entourant la valeur
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]

            self.variables[name] = value

        return self.variables 

    def resolve(self, expression: str):
        """
        Remplace les références $(variable)
        par leur valeur connue.
        """

        pattern = r"\$\(([A-Za-z_]\w*)\)"

        def replace_variable(match):
            name = match.group(1)

            return self.variables.get(
                name,
                match.group(0)
            )

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