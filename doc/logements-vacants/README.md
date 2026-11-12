# Logements et locaux vacants

Commandes d'import des données de locaux et logements vacants.

| Commande | Données |
| --- | --- |
| `locomvac [dirname]` | Locaux vacants commerciaux |
| `lovac [dirname]` | Logements vacants |
| `lovac-fil [dirname] [OPTIONS]` | Fichier LOVAC FIL |

Exemples avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py locomvac
docker compose run --rm urbaflow python urbaflow/main.py lovac
docker compose run --rm urbaflow python urbaflow/main.py lovac-fil /data/ --schema public --table-name lovac_fil --recursive --recreate
```

Un répertoire local peut être passé en argument. Les valeurs par défaut et
les options de schéma, de table et de parcours des fichiers sont affichées
par `--help`. Voir aussi la [fiche technique LOCOMVAC](https://www.collectivites-locales.gouv.fr/sites/default/files/migration/fiche_technique_locaux_vacants_commerciaux_2020.pdf).
