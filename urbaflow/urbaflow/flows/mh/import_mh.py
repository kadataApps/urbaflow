# https://www.data.gouv.fr/fr/datasets/immeubles-proteges-au-titre-des-monuments-historiques-2/
# https://data.culturecommunication.gouv.fr/explore/dataset/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/export/
# https://data.culture.gouv.fr/explore/dataset/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/export/
# https://data.culturecommunication.gouv.fr/explore/dataset/liste-des-jardins-remarquables/export/

# https://data.culturecommunication.gouv.fr/explore/dataset/liste-des-edifices-labellises-architecture-contemporaine-remarquable-acr/export/


# CREATE TABLE saintes.patrimoine_immeubles_proteges_mh AS (
#   SELECT * FROM patrimoine_immeubles_proteges_mh p 
#   WHERE st_intersects(p.geom, (SELECT st_union(geom) from saintes.communes))
#   );
# CREATE INDEX sidx_patrimoine_immeubles_proteges_mh ON saintes.patrimoine_immeubles_proteges_mh using gist(geom);
# ALTER TABLE saintes.patrimoine_immeubles_proteges_mh add primary key(id);