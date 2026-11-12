# Outils PostgreSQL/PostGIS

## Installer les fonctions géométriques de base

La commande `install-base-functions` crée ou met à jour dans le schéma `public`
les fonctions PostGIS `PolygonalMakeValid` et `PolygonalIntersection`. Elles
conservent les composantes polygonales du résultat de leurs opérations
géométriques. Les deux scripts SQL sont exécutés dans une seule transaction :
en cas d'erreur, aucune modification n'est conservée. La commande peut être
relancée.

PostGIS doit être activé dans la base cible et l'utilisateur configuré dans
`.env` doit pouvoir créer des fonctions dans `public`. La connexion utilise
les variables `POSTGRES_*`.

```shell
docker compose run --rm urbaflow python urbaflow/main.py install-base-functions
```

Cette commande n'accepte pas d'option de schéma : les fonctions sont
installées dans `public`.

## Déplacer une table PostgreSQL

[`utils/pgmove-table.sh`](../../utils/pgmove-table.sh) copie une table entre
deux bases en conservant ses principaux éléments de structure. Voir
`./utils/pgmove-table.sh --help` pour les options.
