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
résolveur ne peut pas déterminer reste vide. La deuxième feuille est vide.

Chaque exécution remplace le classeur de destination s’il existe déjà.
Passez le dossier complet pour inclure tous les scripts dans le même classeur.
