# Entreprises et établissements

Commandes d'import des données géolocalisées et descriptives de SIRENE.

| Commande | Données |
| --- | --- |
| `geosirene [dirname] [OPTIONS]` | Établissements géolocalisés |
| `sirene-etablissement [dirname] [OPTIONS]` | Données descriptives des établissements |
| `sirene-unite-legale [dirname] [OPTIONS]` | Données des unités légales |
| `geosirene-detail [OPTIONS]` | Jointure enrichie des établissements et unités légales |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py geosirene --departement 85
docker compose run --rm urbaflow python urbaflow/main.py sirene-etablissement
docker compose run --rm urbaflow python urbaflow/main.py sirene-unite-legale
docker compose run --rm urbaflow python urbaflow/main.py geosirene-detail
```

Les commandes descriptives se lancent après `geosirene` : les données
SIRENE sont volumineuses et les imports sont filtrés selon les tables déjà
présentes. Créer le détail en dernier, après les imports des établissements
et des unités légales. Les options de filtrage et les noms de tables sont
consultables avec `--help`.
