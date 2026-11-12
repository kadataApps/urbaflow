# Foncier et cadastre

Commandes d'import des données foncières et cadastrales : MAJIC, DVF,
entités topographiques DGFiP et contours cadastraux.

| Commande | Données |
| --- | --- |
| `majic [dirname] [steps...]` | Données MAJIC et traitements cadastraux associés |
| `dvf <departements> [dirname]` | Demandes de valeurs foncières par département |
| `dgfip-topo [dirname]` | Entités topographiques DGFiP |
| `dgfip-geoparquet [OPTIONS]` | Contours des communes, sections et bâtiments cadastraux |
| `parcelles-historique [OPTIONS]` | Historique des parcelles, y compris celles qui ont disparu |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py majic /data/
docker compose run --rm urbaflow python urbaflow/main.py dvf 35 /data/
docker compose run --rm urbaflow python urbaflow/main.py dgfip-topo
docker compose run --rm urbaflow python urbaflow/main.py dgfip-geoparquet --communes 35001,35238
docker compose run --rm urbaflow python urbaflow/main.py parcelles-historique --departement 35
```

`majic` accepte une liste d'étapes pour limiter le traitement. `dgfip-topo`
télécharge sa source par défaut ; un répertoire local peut être fourni à la
place. `dgfip-geoparquet` accepte un périmètre par communes, EPCI ou
département. Les paramètres détaillés sont disponibles avec `--help`.
`parcelles-historique` intègre les millésimes par département et dans l'ordre
chronologique ; par défaut, il importe les millésimes publiés qui n'ont pas
encore été chargés. On peut limiter les départements avec `-d` et les dates
avec `-m` (`AAAA-MM-JJ`). Les périodes d'existence des parcelles sont
consultables via `dgfip_parcelle_historique` et la fonction
`dgfip_parcelles_au_millesime(date)`.

Cet historique peut servir à la
[géolocalisation des autorisations SITADEL](../urbanisme/README.md#géolocalisation-sitadel-par-les-parcelles-historiques)
avec la commande `sitadel-geolocate`.

Documentation détaillée :

- [Traitements MAJIC et Fichiers Fonciers](../../MAJIC.md)
- [Données DGFiP TOPO](../../DGFiP_TOPO.md)
