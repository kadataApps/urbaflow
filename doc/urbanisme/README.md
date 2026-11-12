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
| `sitadel-indicators [source_file] [OPTIONS]` | Indicateurs de logements commencés pour une table de communes |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py banatic-communes
docker compose run --rm urbaflow python urbaflow/main.py docurba-epci 200069193
docker compose run --rm urbaflow python urbaflow/main.py gpu-plu --epci 200071629
docker compose run --rm urbaflow python urbaflow/main.py gpu-sup
docker compose run --rm urbaflow python urbaflow/main.py sitadel
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
