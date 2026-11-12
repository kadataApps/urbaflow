# Équipements, patrimoine et friches

Commandes d'import des équipements, du patrimoine protégé et des friches.

| Commande | Données |
| --- | --- |
| `bpe [dirname] [OPTIONS]` | Base Permanente des Équipements (INSEE) |
| `mh [dirname] [OPTIONS]` | Immeubles protégés au titre des Monuments Historiques |
| `acr [dirname] [OPTIONS]` | Architecture Contemporaine Remarquable |
| `cartofriches [dirname] [OPTIONS]` | Sites référencés dans Cartofriches |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py bpe
docker compose run --rm urbaflow python urbaflow/main.py mh
docker compose run --rm urbaflow python urbaflow/main.py acr
docker compose run --rm urbaflow python urbaflow/main.py cartofriches
```

Ces commandes téléchargent leurs sources par défaut. Un répertoire local,
un schéma, un nom de table et le comportement de recréation peuvent être
précisés selon la commande ; voir `--help`.
