# DGFiP TOPO

La donnée DGFiP TOPO est un fichier CSV contenant la liste des entités topographiques de la DGFiP, nécessaire pour le traitement des données MAJIC.
Il remplace le fichier Fantoir.

Source: <https://data.economie.gouv.fr/explore/assets/topo-fichier-des-entites-topographiques/>

Lien direct au format CSV <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/topo-fichier-des-entites-topographiques/exports/csv/?delimiter=%3B&lang=fr&timezone=Europe%2FParis&use_labels=true>

Pour importer les entités topographiques DGFiP, nécessaires au traitement MAJIC, placer le fichier `topo-fichier-des-entites-topographiques.csv` dans le répertoire défini par `PATH_TO_DATA`, puis exécuter :

```shell
docker compose run --rm urbaflow python urbaflow/main.py dgfip-topo /data/
```