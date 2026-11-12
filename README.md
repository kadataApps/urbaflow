# UrbaFlow

UrbaFlow est un ETL Python/SQL qui importe des données territoriales et
d'urbanisme dans PostgreSQL/PostGIS. Les commandes CLI sont documentées par
thématique :

- [Foncier et cadastre](doc/foncier/README.md) : MAJIC, DVF, DGFiP TOPO,
  parcelles cadastrales et historique parcellaire.
- [Urbanisme et servitudes](doc/urbanisme/README.md) : documents d'urbanisme,
  GPU, référentiels communaux et données SITADEL.
- [Risques et environnement](doc/risques/README.md) : risques naturels,
  technologiques et pollution des sols.
- [Géographie, bâti et occupation du sol](doc/geographie/README.md) : BD TOPO
  et OCS GE.
- [Entreprises et établissements](doc/entreprises/README.md) : GeoSIRENE et
  SIRENE.
- [Logements et locaux vacants](doc/logements-vacants/README.md) : LOVAC et
  LOCOMVAC.
- [Équipements, patrimoine et friches](doc/equipements-patrimoine/README.md) :
  BPE, monuments historiques, ACR et Cartofriches.
- [Outils PostgreSQL/PostGIS](doc/outils/README.md) : fonctions géométriques et
  migration de tables.

## Démarrage

Les traitements sont exécutés dans le conteneur Docker `urbaflow`. Il est
également possible de travailler en local avec [uv](https://docs.astral.sh/uv/)
et les dépendances géospatiales nécessaires.

1. Copier `.env.example` vers `.env`, puis renseigner `PATH_TO_DATA` et les
   paramètres de connexion `POSTGRES_*`. Les données de `PATH_TO_DATA` sont
   montées dans le conteneur sous `/data`.
2. Si nécessaire, démarrer une base PostGIS locale avec `make start-postgis`.
   Avec Docker Compose, garder `POSTGRES_HOST=postgis` ; pour une base sur
   l'hôte, utiliser `POSTGRES_HOST=host.docker.internal`.
3. Définir au besoin `IMPORT_SCHEMA` (schéma cible par défaut, `public` si
   absent). Pour MAJIC, `MAJIC_SCHEMA` définit le schéma de travail (`majic`
   par défaut), distinct du schéma cible. Voir la
   [documentation MAJIC](MAJIC.md).
4. Construire l'image avec `make build-urbaflow`.

Afficher l'aide CLI ou celle d'une commande :

```shell
docker compose run --rm urbaflow python urbaflow/main.py --help
docker compose run --rm urbaflow python urbaflow/main.py <commande> --help
```

Pour le développement local :

```shell
cd urbaflow
uv sync
uv run python urbaflow/main.py --help
```

## Licence

© Thomas Brosset - [thoomasbro](https://github.com/thoomasbro) - [KADATA](https://kadata.fr) - 2025

© Pierre Camilleri - [pierrecamilleri](https://github.com/pierrecamilleri) - [Multi](https://multi.coop) - 2023

Ce logiciel est distribué sous la licence CeCILL v2.1, compatible avec le droit français. Vous pouvez utiliser, modifier et distribuer ce logiciel selon les termes de la licence CeCILL. Toute modification ou distribution de ce logiciel doit être soumise aux mêmes conditions. Pour plus de détails, veuillez consulter le texte complet de la licence CeCILL à l'adresse suivante : [http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html](http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html). English version: [https://spdx.org/licenses/CECILL-2.1.html#licenseText](https://spdx.org/licenses/CECILL-2.1.html#licenseText)
