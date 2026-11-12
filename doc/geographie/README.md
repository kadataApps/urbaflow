# Géographie, bâti et occupation du sol

Commandes d'import des référentiels géographiques IGN et des données
d'occupation du sol.

| Commande | Données |
| --- | --- |
| `bdtopo-batiment [OPTIONS]` | Bâtiments de la BD TOPO® |
| `bdtopo-troncon-route -d <departement> [OPTIONS]` | Tronçons de route de la BD TOPO® |
| `ocsge [OPTIONS]` | Occupation du sol à grande échelle |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py bdtopo-batiment --departement 35
docker compose run --rm urbaflow python urbaflow/main.py bdtopo-troncon-route --departement 35
docker compose run --rm urbaflow python urbaflow/main.py ocsge --epci 243500139
```

Les commandes `bdtopo-batiment` et `ocsge` acceptent un périmètre par
département, EPCI ou communes. `bdtopo-troncon-route` prend un seul
département. Elles téléchargent les données IGN par défaut ; consulter
`--help` pour les options de millésime, de schéma et de conservation des
fichiers téléchargés.
