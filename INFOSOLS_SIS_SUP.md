# Documentation des données Géorisques INFOSOLS (SIS et SUP)

Ce document décrit l'intégration des données relatives aux **SIS** (Secteurs d'Information sur les Sols) et aux **SUP** (Servitudes d'Utilité Publique) issues de la plateforme **Géorisques**.

---

## 1. Présentation des jeux de données

- **SIS (Secteurs d'Information sur les Sols)** : Zones d'une commune ou d'un territoire répertoriées par l'État où la connaissance de la pollution des sols nécessite la réalisation d'études de sols et de mesures de gestion de la pollution en cas de changement d'usage ou de projet d'aménagement.
- **SUP (Servitudes d'Utilité Publique)** : Limitations administratives au droit de propriété instaurées sur les sols ou sous-sols pollués au titre du Code de l'environnement (ex-sites industriels BASOL/BASIAS).

---

## 2. Sources et Services Web Géorisques

Les données sont interrogées dynamiquement via l'API Web service de Géorisques :

- **Recherche par département (JSON)** :
  - **SIS** : `https://www.georisques.gouv.fr/webappReport/ws/infosols/resultats/recherche?type=classification&statut=SIS&codeDepartement={code_departement}`
  - **SUP** : `https://www.georisques.gouv.fr/webappReport/ws/infosols/resultats/recherche?type=classification&statut=SUP&codeDepartement={code_departement}`

- **Fiche détaillée individuelle (BRGM)** :
  - URL d'accès direct : `https://fiches-risques.brgm.fr/georisques/infosols/classification/{identifiant_ssp}`

---

## 3. Schéma de la Base de Données PostGIS

Les flux créent et alimentent les tables `risques_sis` et `risques_sup` dans le schéma PostGIS configuré (par défaut `public`).

### Modèle de données

| Nom de colonne | Type | Description | Exemple |
| :--- | :--- | :--- | :--- |
| `identifiant_ssp` | `text PRIMARY KEY` | Identifiant unique SSP du site | `SSP00047400101` |
| `identifiant_sis` | `text` | Identifiant local du secteur d'information | `85SIS07064` |
| `statut` | `text` | Code de la classification (`SIS` ou `SUP`) | `SIS` |
| `statut_definition` | `text` | Définition / libellé complet du statut | `Secteur d'information sur les sols` |
| `nom_usuel` | `text` | Nom usuel de l'établissement ou du site | `MAIRIE Nesmy (ex froger)` |
| `code_insee` | `text` | Code(s) INSEE de la commune rattachée | `85160` |
| `nom_commune` | `text` | Nom(s) de la commune rattachée | `NESMY` |
| `code_departement` | `text` | Code du département | `85` |
| `nom_departement` | `text` | Nom du département | `VENDEE` |
| `code_region` | `text` | Code INSEE de la région | `52` |
| `nom_region` | `text` | Nom de la région | `PAYS DE LA LOIRE` |
| `adresse` | `text` | Nom de la voie / rue | `RUE DES TUILERIES` |
| `numero_voie` | `text` | Numéro dans la voie | `37` |
| `code_postal` | `text` | Code postal | `85310` |
| `complement_adresse` | `text` | Complément d'adresse ou lieu-dit | `LA BRETAUDIÈRE` |
| `date_maj` | `date` | Date de la dernière mise à jour | `2020-09-29` |
| `url_fiche` | `text` | URL d'accès direct à la fiche détaillée | `https://fiches-risques.brgm.fr/georisques/infosols/classification/SSP00047400101` |
| `bbox_geojson` | `text` | Emprise géométrique brute au format GeoJSON | `{"type": "Polygon", "coordinates": [...]}` |
| `geom` | `geometry(GEOMETRY, 2154)` | Polygone/MultiPolygone reprojeté en Lambert 93 | *Geom PostGIS (EPSG:2154)* |

### Reprojection et Géométrie PostGIS

Le polygone d'instruction fourni dans la clé `bboxInstruction` du JSON Géorisques est exprimé dans la projection **Web Mercator (`EPSG:3857`)**.

Lors de l'import, PostGIS effectue automatiquement la transformation vers la projection française **Lambert 93 (`EPSG:2154`)** :

```sql
UPDATE {schema}.{table_name}
SET geom = ST_Multi(ST_Transform(
    ST_SetSRID(ST_GeomFromGeoJSON(bbox_geojson), 3857),
    2154
))
WHERE bbox_geojson IS NOT NULL AND bbox_geojson != '';
```

Un index spatial GIST `sidx_{table_name}_geom` est créé automatiquement sur la colonne `geom`.

---

## 4. Utilisation des Commandes CLI

### Données SIS (Secteurs d'Information sur les Sols)

- **Avec Docker** :
  ```shell
  docker compose run --rm urbaflow python urbaflow/main.py risques-sis -d 85
  ```

- **En local** :
  ```shell
  cd urbaflow && uv run python urbaflow/main.py risques-sis -d 85
  ```

### Données SUP (Servitudes d'Utilité Publique)

- **Avec Docker** :
  ```shell
  docker compose run --rm urbaflow python urbaflow/main.py risques-sup -d 85
  ```

- **En local** :
  ```shell
  cd urbaflow && uv run python urbaflow/main.py risques-sup -d 85
  ```

### Options disponibles

- `-d, --departement TEXT` : Code du département à télécharger (ex: `85`, `75`).
- `dirname` (optionnel) : Repertoire local contenant des fichiers JSON pré-téléchargés.
- `--schema TEXT` : Nom du schéma de destination (défaut : `public`).
- `--table-name TEXT` : Nom de la table PostGIS (défaut : `risques_sis` ou `risques_sup`).
- `--recreate / --no-recreate` : Supprimer et recréer la table si elle existe (défaut : `--no-recreate`).
