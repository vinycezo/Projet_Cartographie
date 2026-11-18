# Projet_Cartographie
Cartographie des tables à partir de Script Qlik

## Export Excel

```sh
python -m pip install openpyxl
python export_cartographie.py "chemin/vers/le/dossier" -o cartographie.xlsx
```

Le script lit les fichiers `.qvs` du dossier et utilise leur nom sans
extension comme nom d’application. Pour tester un seul script, indiquez
directement le chemin du fichier `.qvs` ou `.txt`.

La feuille **Variables** contient une ligne par application quand une seule
entrée et une seule sortie sont utilisées. Les couples distincts sont
conservés quand les variables ou leurs valeurs diffèrent.
Les valeurs sont résolues au point d’utilisation. Une valeur que le
résolveur ne peut pas déterminer reste vide.

La feuille **Feuille 2** contient les colonnes `Application`, `Table_source`,
`table_sortie`, `Source`, `where` et `output`. Pour une lecture SQL,
`Table_source` indique la table SQL lue. Pour une lecture de fichier, `Source`
indique le chemin du fichier écrit dans le `FROM`, ou le nom de la variable
si le chemin en utilise une. La colonne `output` indique la variable du chemin
de sortie utilisée par le `STORE`, si elle existe. Ce nom correspond à la
colonne `output` de la feuille **Variables**.

Chaque exécution remplace le classeur de destination s’il existe déjà.
Passez le dossier complet pour inclure tous les scripts dans le même classeur.
