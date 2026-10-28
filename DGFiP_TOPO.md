# DGFiP TOPO

La donnée DGFiP TOPO est un fichier CSV contenant la liste des entités topographiques de la DGFiP, nécessaire pour le traitement des données MAJIC.
Il remplace le fichier Fantoir.

Source : <https://www.data.gouv.fr/datasets/fichier-des-entites-topographiques-topo-dgfip-1>

Lien direct au format CSV : <https://www.data.gouv.fr/api/1/datasets/r/906e5bd0-8be8-4150-9956-594fa0e8154c>

Pour télécharger automatiquement le fichier et importer les entités topographiques DGFiP, nécessaires au traitement MAJIC, exécuter sans argument :

```shell
docker compose run --rm urbaflow python urbaflow/main.py dgfip-topo
```

Le fichier `topo-fichier-des-entites-topographiques.csv` est téléchargé dans le sous-répertoire `dgfip_topo` du répertoire temporaire de l'application.

Pour utiliser un fichier local sans téléchargement, placer le CSV dans le répertoire défini par `PATH_TO_DATA`, puis fournir explicitement le répertoire :

```shell
docker compose run --rm urbaflow python urbaflow/main.py dgfip-topo /data/
```