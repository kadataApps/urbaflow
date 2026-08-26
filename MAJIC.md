# Documentation des traitements issus des Fichiers Fonciers (FF) du CEREMA et des traitements MAJIC à l'aide du plugin QgisCadastre

L'ensemble des traitements des données MAJIC s'inspire des travaux de la DGFiP, du CEREMA et du groupe national de travail sur les données foncières.

<https://doc-datafoncier.cerema.fr/doc/ff/>

Un certain nombre de requêtes d'import sont issues du plugin <https://github.com/3liz/QgisCadastrePlugin> (en licence GPL).

Dans la mesure du possible, le nom des colonnes et les traitements ont été conservés pour faciliter la maintenance et la compréhension des traitements.

## Lancement des traitements

Lancer le traitement MAJIC complet :

```shell
docker compose run --rm urbaflow python urbaflow/main.py majic /data/
```

Cette commande exécute le CLI dans l'image contenant les bibliothèques géospatiales et supprime le conteneur à la fin de l'import.

Pour n'exécuter que certaines étapes MAJIC, ajouter leurs identifiants à la commande :

```shell
docker compose run --rm urbaflow python urbaflow/main.py majic /data/ step1 step2
```

## Description des étapes de processing des données MAJIC

Il est possible de sélectionner les étapes à lancer ou non.
Par défaut, toutes les étapes sont lancées.

Options:

- step1  : Copie des scripts dans le répertoire temporaire
           (pour adaptation des scripts en fonction des
           paramètres d'import)
- step2  : Import données brutes (6 fichiers) dans 6 tables
           temporaires dans PostgreSQL
- step3  : nettoyage éventuel des tables métiers préexistantes
- step4  : Initialisation de la base avec tables métiers
- step5  : Formatage des données MAJIC
- step6  : Identification des communes pour lesquelles les données
           MAJIC ont été importées, téléchargement et import 
           des données cadastre (vecteurs)
- step7  : Fusion des données Cadastre et MAJIC
- step8  : Intégration des données parcelles,
           proprietaires et local dans le schema Public
- step9 : Téléchargement et import des données bati
           (vecteurs)
- step10 : Intégration des données bati dans le schéma Public
- step11 : Nettoyage des fichiers temporaires et des tables

Exemple d'utilisation:

- import seulement des données brutes dans postgresql:

```shell
docker compose run --rm urbaflow python urbaflow/main.py majic /data/ step1 step2
```
## Nommage des fichiers

Les fichiers MAJIC importés doivent être nommés selon le format suivant:

```
"bati": "BATI",
"nbati": "NON_BATI",
"pdll": "PDL_LOTS",
"lotlocal": "LLOC",
"prop": "PROP",
````
Si besoin, cela peut être configuré dans le fichier `urbaflow/urbaflow/config.py` en modifiant la variable `MAJIC_FILE_NAMES`.

## Champs complémentaires

### descprop

Description de la nature du droit de propriété.

Modalités:

- COPROPRIETE
- INDIVISION
- LITIGE
- BAIL EMPHYTHEOTIQUE
- SEPARATION NUE-PROPRIETE / USUFRUIT
- PLEINE PROPRIETE
- AUTRE

### catpro

Retraitement de la classification automatique des propriétaires.
Une requête manuelle permet d'identifier les propriétaires publics ou parapublics qui ont été incorrectement catégorisés dnas les fichiers MAJIC source.
L'identification se fait essentiellement sur le nom de la personne morale.

#### typologie retenue

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

### catpro_niv2

Cette typologie a été initialement élaborée pour répondre au besoin d'analyse foncière de la FAB.
Typologie retenue:

- Copropriété/ASL (suite à nos discussions, nous pouvons pousser la recherche aux copropriétés/ASL simples et complexes avec par exemple une tranche simple allant jusqu’à 5 copropriétaires/colotis)
- Personnes morales
- Monopropriété (propriétaire physique unique)
- Monopropriété (personne morale unique)
- Indivision simple (2 pers.)
- Indivision complexe (+ de 2 pers.)
- Groupements de personnes morales
- Public (regroupant l’ensemble des acteurs publics, pas de nécessité de les distinguer)
- Parapublics (regroupant organismes HLM, SNCF, SEM etc.)
- Droits démembrés (ex: nue-propriété/usufruit, bail emphytéotique)
