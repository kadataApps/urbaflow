# UrbaFlow

ETL de traitement des données liées à l'urbanisme :

- MAJIC
- DVF (données Valeurs Foncières)
- DGFiP TOPO
- FFPM (Fichiers Fonciers Personnes Morales)
- Cadastre
- Bati
- PLU
- Géosirene

L'ETL est composé de scripts python et de fichiers SQL.
Il a été testé pour les environnements linux et OSX.

UrbaFlow vient avec quelques utilitaires pour faciliter la gestion des bases de données PostgreSQL/PostGIS, notamment `pgmove-table.sh` qui permet de déplacer simplement une table d'une base à une autre en gérant les dépendances (contraintes, index, séquences...) et la destination (nom du schéma et de la table).

## Prérequis

- Docker : permet de lancer les scripts dans un environnement maitrisé avec les bonnes dépendances.
  - (installation sur windows: [https://docs.docker.com/desktop/install/windows-install/])
  - (installation sur mac: [https://docs.docker.com/desktop/install/mac-install/])
  - (installation sur linux: [https://docs.docker.com/engine/install/])
- (optionnel) Make (installation sur windows: [https://chocolatey.org/packages/make])

Pour le développement local, installer [uv](https://docs.astral.sh/uv/).

```shell
cd urbaflow
uv sync
```

Les commandes locales s'exécutent avec `uv run`, par exemple `uv run ruff check`.

## Principe

Les fichiers SQL sont copiés, puis certaines parties de ces fichiers sont remplacées/réécrites (changement de "variables", notamment les dates, schémas...) avant d'être exécutées.

L'ETL est exécuté dans une image Docker afin d'utiliser un environnement maîtrisé, incluant notamment GEOS et GDAL. Les dépendances Python sont installées dans l'image avec `uv` à partir de `urbaflow/pyproject.toml` et `urbaflow/uv.lock`.

Les scripts sont lancés via une ligne de commande depuis un container docker.

Les données sources sont montées dans un volume attaché au container dans le répertoire `/data`.

L'ETL charge les données dans une base PostGIS qui doit être configurée dans les variables d'environnement.

## Documentation

### GeoSIRENE

[Base SIRENE des établissements (SIRET) - géolocalisée avec la Base d'Adresse Nationale (BAN)](https://www.data.gouv.fr/fr/datasets/base-sirene-des-etablissements-siret-geolocalisee-avec-la-base-dadresse-nationale-ban/)

Jeu de données: <https://files.data.gouv.fr/geo-sirene/last/dep/>

### LOCOMVAC

[documentation LOCOMVAC sur le site collectivites-locales.gouv.fr](https://www.collectivites-locales.gouv.fr/sites/default/files/migration/fiche_technique_locaux_vacants_commerciaux_2020.pdf)

## Exécuter l'ETL avec Docker

Les commandes d'import sont exécutées dans le conteneur `urbaflow`. Les données définies par `PATH_TO_DATA` sont disponibles dans le conteneur sous `/data`.

1. Créer le fichier `.env` à la racine du projet à partir de `.env.example`, puis renseigner les variables suivantes :
    - le chemin des fichiers majic à charger avec la variable `PATH_TO_DATA`. Le
      chemin sera monté dans le conteneur sur `/data/`.
    - Configuration de la base de données :
      - Si besoin d'une base postgis à la volée, lancer la base PostGIS avec Docker `make start-postgis` (cette base est
      exposée sur le port 5432).
      - si la base de données est lancée avec docker-compose, conserver `POSTGRES_HOST=postgis`
      - si la base de données n'est pas lancée avec le même docker compose, utiliser `POSTGRES_HOST=host.docker.internal` pour rediriger vers le host de l'hôte (la machine qui exécute le container)
      - Configurer également : `POSTGRES_USER`, `POSTGRES_PASS`, `POSTGRES_DB`, `POSTGRES_PORT` (les mêmes variables sont utilisées pour le lancement de la base de données avec docker-compose et pour le lancement de l'image de processing)
      - Configurer également : `IMPORT_SCHEMA` (schéma de la base de données dans lequel les données seront importées)
2. Construire l'image :

```shell
make build-urbaflow
```

3. Lancer la commmande d'import souhaitée :

- MAJIC: cf. [MAJIC.md](MAJIC.md)
- DGFIP TOPO: cf. [DGFiP_TOPO.md](DGFiP_TOPO.md)

4. Pour ouvrir un shell de diagnostic dans l'image :

```shell
make urbaflow
```

## Commandes disponibles (CLI `main.py`)

Le point d'entrée CLI est `urbaflow/main.py` (Typer).

### Lancement de la CLI

- Avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py --help
```

- En local (développement) :

```shell
uv run python urbaflow/main.py --help
```

### Commandes

- `dvf <departements> [dirname]`
  - Importe les données DVF pour un ou plusieurs départements.
  - `dirname` est optionnel (par défaut: `/data/`).

- `dgfip-topo [dirname]`
  - Importe les entités topographiques DGFiP.
  - `dirname` est optionnel (par défaut: `/data/`).

- `locomvac [dirname]`
  - Importe les fichiers LOCOMVAC.
  - `dirname` est optionnel (par défaut: `/data/`).

- `lovac [dirname]`
  - Importe les fichiers LOVAC.
  - `dirname` est optionnel (par défaut: `/data/`).

- `lovac-fil [dirname] [OPTIONS]`
  - Importe les données LOVAC FIL.
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `lovac_fil`)
    - `--recursive / --no-recursive` (défaut: `--no-recursive`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `majic [dirname] [steps...]`
  - Importe MAJIC/Cadastre.
  - `steps` permet de limiter l'exécution à certaines étapes.

- `risques-cavite [dirname] [OPTIONS]`
  - Importe les données de risques de cavités.
  - Fournir soit `dirname`, soit `--department`.
  - Options :
    - `-d, --department TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_cavite`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `risques-rga [dirname] [OPTIONS]`
  - Importe les données de retrait-gonflement des argiles.
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-remnappes [dirname] [OPTIONS]`
  - Importe les données de risques d'inondation par remontée de nappe (REMNAPPES).
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_remnappes`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

### Exemples

```shell
# Aide générale
docker compose run --rm urbaflow python urbaflow/main.py --help

# Commande MAJIC (toutes les étapes)
docker compose run --rm urbaflow python urbaflow/main.py majic /data/

# Risques cavités pour un département
docker compose run --rm urbaflow python urbaflow/main.py risques-cavite -d 85

# LOVAC FIL avec options
docker compose run --rm urbaflow python urbaflow/main.py lovac-fil /data/ --schema public --table-name lovac_fil --recursive --recreate
```
## Licence

© Thomas Brosset - [thoomasbro](https://github.com/thoomasbro) - [KADATA](https://kadata.fr) - 2025
© Pierre Camilleri - [pierrecamilleri](https://github.com/pierrecamilleri) - [Multi](https://multi.coop) - 2023

Ce logiciel est distribué sous la licence CeCILL v2.1, compatible avec le droit français. Vous pouvez utiliser, modifier et distribuer ce logiciel selon les termes de la licence CeCILL. Toute modification ou distribution de ce logiciel doit être soumise aux mêmes conditions. Pour plus de détails, veuillez consulter le texte complet de la licence CeCILL à l'adresse suivante : [http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html](http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html). English version: [https://spdx.org/licenses/CECILL-2.1.html#licenseText](https://spdx.org/licenses/CECILL-2.1.html#licenseText)
