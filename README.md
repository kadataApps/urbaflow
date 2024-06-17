# UrbaFlow

ETL de traitement des données liées à l'urbanisme :

- MAJIC
- DVF (données Valeurs Foncières)
- Fantoir
- FFPM (Fichiers Fonciers Personnes Morales)
- Cadastre
- Bati
- PLU
- Géosirene

L'ETL est composé de scripts python et de fichiers SQL.
Il a été testé pour les environnements linux et OSX.

## Prérequis

- Git (installation sur windows: [https://gitforwindows.org/])
  (git permet de cloner le projet, mais également de disposer facilement de la commande make sous windows, accessible depuis git bash)
- Docker (installation sur windows: [https://docs.docker.com/desktop/install/windows-install/])

## Principe

Les fichiers SQL sont copiés, puis certaines parties de ces fichiers sont remplacées/réécrites (changement de "variables", notamment les dates, schémas...) avant d'être exécutées.

L'ETL a été dockerisé afin de pouvoir se lancer quelque soit l'environnement en maitrisant les dépendances installées, notamment GDAL (utilisation de l'image de base `osgeo/gdal:ubuntu-small-3.2.1`).

Les scripts sont lancés via une ligne de commande depuis un container docker.

Les données sources sont montées dans un volume attaché au container dans le répertoire `/data`.

L'ETL charge les données dans une base PostGIS qui doit être configurée dans les variables d'environnement.

## Documentation

### Documentation des traitements issus des Fichiers Fonciers (FF) du CEREMA et des traitements MAJIC à l'aide du plugin QgisCadastre

L'ensemble des traitements des données MAJIC s'inspire des travaux de la DGFiP, du CEREMA et du groupe national de travail sur les données foncières.

<https://doc-datafoncier.cerema.fr/doc/ff/>

Un certain nombre de requêtes d'import sont issues du plugin <https://github.com/3liz/QgisCadastrePlugin> (en licence GPL).

Dans la mesure du possible, le nom des colonnes et les traitements ont été conservés pour faciliter la maintenance et la compréhension des traitements.

### Champs complémentaires

#### descprop

Description de la nature du droit de propriété.

Modalités:

- COPROPRIETE
- INDIVISION
- LITIGE
- BAIL EMPHYTHEOTIQUE
- SEPARATION NU-PROPRIETE / USUFRUIT
- PLEINE PROPRIETE
- AUTRE

#### typproprietaire

Retraitement de la classification automatique des propriétaires.
Une requête manuelle permet d'identifier les propriétaires publics ou parapublics qui ont été incorrectement catégorisés dnas les fichiers MAJIC source.
L'identification se fait essentiellement sur le nom de la personne morale.

##### typologie retenue

La typologie a été réalisée dans le cadre d'une logique d'analyse foncière en vue de la réalisation d'opérations d'urbanisme, du point de vue de la collectivité (EPCI ou commune), pour laquelle la question de la maîtrise foncière est importante.

Foncier considéré comme maitrisé :

- COMMUNE
- EPCI
- EPF
- AMENAGEUR_PUB (Aménageur public, type EPA, SEM locales ou autres identifiés comme aménageurs partenaires)

Foncier considéré comme non maitrisé :

- AUTRE_PUB: autres personnes morales de droit public
  - état, région, département
  - mais aussi éventuellement autres SEM,SIVOM/SIVU? CCAS ?
  - bailleurs sociaux, etc, non considérés comme partenaires ?
- PRIVE (personnes morales ou publiques sans distinction)
- COPROPRIETE

#### typproprietaire_niv2

Cette typologie vise à répondre au besoin d'analyse foncière de la FAB.
Typologie retenue:

- Copropriétés/ASL (suite à nos discussions, nous pouvons pousser la recherche aux copropriétés/ASL simples et complexes avec par exemple une tranche simple allant jusqu’à 5 copropriétaires/colotis)
- Sociétés
- Monopropriétés
- Indivisions simples (2 pers.)
- Indivisions complexes (+ de 2 pers.)
- Groupements de sociétés
- Public (regroupant l’ensemble des acteurs publics, pas de nécessité de les distinguer)
- Parapublics (regroupant organismes HLM, SNCF, SEM etc.)

## Processing

Les étapes suivantes permettent de lancer le processus avec un containeur docker.

1. Créer à la racine du projet le fichier `.env` à partir de `.env.example` et modifier les variables d'environnement suivantes:
    - le chemin des fichiers majic à charger avec la variable `PATH_TO_DATA`. Le
      chemin sera monté dans le container sur `/data/`.
    - Configuration de la base de données :
      - Si besoin d'une base postgis à la volée, lancer la base PostGIS avec Docker `make start-postgis` (cette base est
      exposée à l'adresse ip publique du containeur sur le port 5432).
      - si la base de données est lancée avec docker-compose, conserver `POSTGRES_HOST=postgis`
      - si la base de données n'est pas lancée avec le même docker compose, utiliser `POSTGRES_HOST=host.docker.internal` pour rediriger vers le host de l'hôte (la machine qui exécute le container)
      - Configurer également : `POSTGRES_USER`, `POSTGRES_PASS`, `POSTGRES_DB`, `POSTGRES_PORT` (les mêmes variables sont utilisées pour le lancement de la base de données avec docker-compose et pour le lancement de l'image de processing)
      - Configurer également : `POSTGRES_SCHEMA` (schéma de la base de données dans lequel les données seront importées)
2. Lancer l'image de processing via la commande `make urbaflow`

   Cela permet d'accéder à un environnement bash dans lequel les libs pythons
   sont installées et les scripts python d'import des données peuvent être
   lancés.

3. Lancer les commandes d'import et de traitement des données
  
- Lancer le traitement des données MAJIC avec :

```python
python main.py majic /data/
```
  
- Initialiser les tables [FANTOIR][fantoir] (nécessaire pour le traitement
    des données MAJIC) avec :

 ```python
 python src/main.py fantoir
 ```

[fantoir]: https://www.data.gouv.fr/fr/datasets/fichier-fantoir-des-voies-et-lieux-dits/

## Description des étapes de processing des données MAJIC

Il est possible de sélectionner les étapes à lancer ou non.
Par défaut, toutes les étapes sont lancées.

Options:
  
- --step1 / --no-step1    Import données brutes (6 fichiers) dans 6 tables
                            temporaires dans PostgreSQL
- --step2 / --no-step2    Copie des scripts dans le répertoire temporaire
                            (pour adaptation des scripts en fonction des
                            paramètres d'import)
- --step3 / --no-step3    nettoyage éventuel des tables métiers préexistantes
- --step4 / --no-step4    Initialisation de la base avec tables métiers
- --step5 / --no-step5    Formatage des données MAJIC
- --step6 / --no-step6    Identification des communes importées via MAJIC
- --step7 / --no-step7    Téléchargement et import des données cadastre
                             (vecteurs)
- --step8 / --no-step8    Fusion des données Cadastre et MAJIC
- --step9 / --no-step9    Intégration des données parcelles,
                            proprietaires et local dans le schema Public
- --step10 / --no-step10  Téléchargement et import des données bati
                             (vecteurs)
- --step11 / --no-step11  Intégration des données bati dans le schéma Public
- --step12 / --no-step12  Nettoyage des fichiers temporaires et des tables

Exemple d'utilisation:

- import seulement des données brutes dans postgresql:

```shell
python main.py majic /data/ --no-step2 --no-step3 --no-step4 --no-step5 --no-step6 --no-step7 --no-step8 --no-step9 --no-step10 --no-step11 --no-step12
```

## Licence

Ce logiciel est distribué sous la licence CeCILL v2.1, compatible avec le droit français. Vous pouvez utiliser, modifier et distribuer ce logiciel selon les termes de la licence CeCILL. Toute modification ou distribution de ce logiciel doit être soumise aux mêmes conditions. Pour plus de détails, veuillez consulter le texte complet de la licence CeCILL à l'adresse suivante : [http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html](http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html). English version: [https://spdx.org/licenses/CECILL-2.1.html#licenseText](https://spdx.org/licenses/CECILL-2.1.html#licenseText)
