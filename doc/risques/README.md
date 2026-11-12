# Risques et environnement

Commandes d'import des données de risques naturels, technologiques et de
pollution des sols.

| Commande | Données |
| --- | --- |
| `risques-cavite` | Cavités |
| `risques-rga` | Retrait-gonflement des argiles |
| `risques-remnappes` | Remontées de nappes |
| `risques-mvt` | Mouvements de terrain |
| `risques-casias` | Anciens sites industriels et activités de service |
| `risques-sis` | Secteurs d'information sur les sols |
| `risques-sup` | Servitudes d'utilité publique liées aux sols |
| `risques-tri` | Territoires à risque important d'inondation |
| `risques-icpe` | Installations classées pour la protection de l'environnement |
| `risques-irep` | Registre des émissions polluantes |
| `risques-gaspar` | Procédures administratives relatives aux risques |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py risques-cavite --departement 85
docker compose run --rm urbaflow python urbaflow/main.py risques-sis --departement 85
docker compose run --rm urbaflow python urbaflow/main.py risques-irep --year 2024
```

Selon la commande, fournir un répertoire contenant les données ou laisser
l'ETL télécharger la source. Les filtres et options de schéma sont indiqués
par `--help`.

Pour le modèle des tables SIS/SUP, les sources et les détails de conversion
géométrique, voir la [documentation Géorisques INFOSOLS](../../INFOSOLS_SIS_SUP.md).
