# Urbanisme et servitudes

Commandes relatives aux documents d'urbanisme, aux servitudes du Géoportail de
l'Urbanisme et aux référentiels communaux nécessaires à leur intégration.

| Commande | Données |
| --- | --- |
| `banatic-communes [dirname] [OPTIONS]` | Communes et rattachement aux EPCI |
| `epci-gpu <siren> [OPTIONS]` | Communes et documents d'urbanisme d'un EPCI |
| `docurba-epci <siren> [OPTIONS]` | État des documents d'urbanisme d'un EPCI et de ses communes |
| `gpu-plu [OPTIONS]` | PLU géographiques du Géoportail de l'Urbanisme |
| `gpu-sup [dirname] [OPTIONS]` | Servitudes d'utilité publique du Géoportail de l'Urbanisme |
| `sitadel [dirname]` | Téléchargement des séries communales et autorisations détaillées SITADEL |
| `sitadel-geolocate [source_file] [OPTIONS]` | Géolocalisation des autorisations à partir des parcelles historiques |
| `sitadel-indicators [source_file] [OPTIONS]` | Indicateurs de logements commencés pour une table de communes |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py banatic-communes
docker compose run --rm urbaflow python urbaflow/main.py docurba-epci 200069193
docker compose run --rm urbaflow python urbaflow/main.py gpu-plu --epci 200071629
docker compose run --rm urbaflow python urbaflow/main.py gpu-sup
docker compose run --rm urbaflow python urbaflow/main.py sitadel
docker compose run --rm urbaflow python urbaflow/main.py sitadel-geolocate
docker compose run --rm urbaflow python urbaflow/main.py sitadel-indicators
```

`docurba-epci` et `epci-gpu` s'appuient sur les communes de
`banatic-communes`. Pour `gpu-plu`, choisir un seul périmètre : `--epci` ou
`--commune`. Les options détaillées de chaque commande sont disponibles avec
`--help`.

`sitadel` télécharge les huit fichiers nationaux sans les importer en base
(destination par défaut : `urbaflow/temp/sitadel`). `sitadel-indicators`
enrichit une table de communes existante avec les logements commencés sur dix
années révolues ; par défaut, la table est `commune` et la période se termine
à la dernière année civile révolue. Un fichier CSV local et l'année de fin
peuvent être indiqués explicitement.

## Géolocalisation SITADEL par les parcelles historiques

La commande `sitadel-geolocate [source_file]` appelle le flow
`geolocate_sitadel_flow`. Elle nécessite PostGIS et la table
`dgfip_parcelle_historique`, préalablement alimentée par
[`parcelles-historique`](../foncier/README.md).
Sans fichier, seuls les **quatre exports détaillés** SDES sont téléchargés à jour
et géolocalisés : logements, locaux, permis d'aménager et permis de démolir.
Un CSV local permet de traiter un seul export, sans accès réseau.

```shell
# Depuis le répertoire urbaflow : constituer d'abord l'historique souhaité
uv run python urbaflow/main.py parcelles-historique -d 35 --schema cadastre

# Traiter les quatre exports détaillés dans le même schéma
uv run python urbaflow/main.py sitadel-geolocate --schema cadastre

# Traiter un seul CSV local et séparer les schémas source et destination
uv run python urbaflow/main.py sitadel-geolocate \
  temp/sitadel/sitadel_detail_logements.csv \
  --schema public --parcels-schema cadastre --table-name sitadel_geolocalisation
```

Le résultat est enregistré dans `sitadel_geolocalisation` (nom adaptable avec
`--table-name`), dans `IMPORT_SCHEMA`, sinon `public`. Par défaut, les parcelles
sont recherchées dans ce même schéma ; `--parcels-schema` permet de le changer.
La couverture dépend des départements et millésimes déjà importés : les
autorisations hors couverture sont conservées sans géométrie.

Le rapprochement utilise `COMM` et les **25 couples**
`SEC_CADASTRE1`/`NUM_CADASTRE1` à `SEC_CADASTRE25`/`NUM_CADASTRE25`.
Les zéros initiaux des sections et numéros sont normalisés et les références
répétées sont dédoublonnées. Aucun préfixe cadastral `000` n'est supposé :
plusieurs préfixes peuvent exister pour une même section et un même numéro.

Pour chaque référence :

1. Une version dont la période contient `DATE_REELLE_AUTORISATION` est prioritaire
   (début inclus, fin exclue ; méthode `periode`).
2. À défaut, la version temporellement la plus proche est retenue, uniquement
   si elle est unique (`plus_proche`). Ce **repli hors période observée**, notamment
   avant le premier millésime importé, n'atteste pas l'existence de la parcelle
   à la date des travaux ; il est signalé dans le résultat et les logs.
3. Plusieurs candidats de même priorité donnent `ambigu`, sans choix arbitraire.
   Une date absente, une référence invalide ou une parcelle introuvable donnent
   respectivement `date_absente`, `reference_invalide` ou `introuvable`.
   Il n'y a pas de repli sur une adresse ou un centroïde communal, ni de
   reconstitution des fusions de communes ou des filiations de parcelles.

Chaque ligne source est conservée, y compris sans correspondance :

| Colonne | Contenu |
| --- | --- |
| `source_file`, `source_line` | Clé de la ligne dans l'export, sans fusionner les autorisations |
| `authorization_id` | `NUM_DAU`, `NUM_PA` ou `NUM_PD` selon l'export |
| `commune`, `authorization_date` | Code INSEE et date réelle d'autorisation |
| `source_data` | Toutes les colonnes d'origine en JSONB, sans perte des zéros initiaux |
| `reference_count`, `matched_count` | Références distinctes renseignées et références rapprochées |
| `parcel_matches` | Liste JSONB : section, numéro, identifiant cadastral, bornes de millésimes et méthode |
| `geolocation_status` | `complet`, `partiel`, `non_geolocalise` ou `sans_reference` |
| `geom` | Union des parcelles rapprochées, MultiPolygon en Lambert-93 (EPSG:2154) |
| `location` | Point sur la surface de cette union, en EPSG:2154 |
| `longitude`, `latitude` | Coordonnées du point en WGS84 (EPSG:4326) |

Une emprise `partiel` ne représente que les références retrouvées. Un statut
`complet` signifie que toutes les références sont rapprochées, pas que toutes
les méthodes sont `periode` : consulter `parcel_matches` pour la qualité temporelle.
Sans parcelle retenue, toutes les colonnes spatiales restent `NULL`.
Les statuts et méthodes incertaines sont journalisés.

Les CSV sont lus par lots, puis rapprochés en SQL. Une relance remplace
**uniquement les résultats des fichiers traités**, identifiés par leur nom de
fichier : les autres exports sont conservés. Réutiliser le même nom pour
actualiser un export. Les anciennes coordonnées sont effacées si elles ne sont
plus calculables. La publication est transactionnelle et les relances concurrentes
sur une même table sont sérialisées. Un CSV vide, mal formé, sans identifiant,
avec une date non vide invalide ou un historique absent fait échouer le flow
sans remplacer les résultats existants.

Tests ciblés, depuis `urbaflow` :
`PYTHONPATH=urbaflow uv run pytest tests/test_sitadel_geolocation.py tests/test_sitadel.py tests/test_sitadel_indicators.py tests/test_cli.py`.
Définir `DGFIP_TEST_DATABASE_URL` avec une URL SQLAlchemy vers une base PostGIS
de test pour inclure les tests spatiaux ; ils isolent et suppriment leurs schémas.
