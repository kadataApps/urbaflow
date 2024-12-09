# https://www.data.gouv.fr/fr/datasets/base-permanente-des-equipements-1/

# CREATE SCHEMA bpe

# ALTER TABLE bpe.insee_bpe  add column geom geometry(point, 2154);

# UPDATE bpe.insee_bpe set geom = st_transform(
# 	st_setsrid(
# 		st_makepoint(lambert_x::numeric, lambert_y::numeric), epsg::integer),2154)
# 		WHERE lambert_x is not null and lambert_x not like '';
# CREATE INDEX sidx_insee_bpe_geom on bpe.insee_bpe using gist(geom);

# DROP TABLE IF EXISTS saintes.insee_bpe;
# CREATE TABLE saintes.insee_bpe AS
# 	SELECT * FROM bpe.insee_bpe b
# 		WHERE st_intersects(b.geom,
# 			(SELECT st_transform(st_union(c.geom),2154)
# 				FROM saintes.communes c));


# CREATE INDEX sidx_insee_bpe_geom on saintes.insee_bpe using gist(geom);
# ALTER TABLE saintes.insee_bpe add primary key (id);


# DROP TABLE IF EXISTS fab.insee_bpe;
# CREATE TABLE fab.insee_bpe AS
# 	SELECT * FROM bpe.insee_bpe b
# 		WHERE st_intersects(b.geom,
# 			(SELECT st_transform(st_union(c.geom),2154)
# 				FROM fab.communes c));


# CREATE INDEX sidx_insee_bpe_geom on fab.insee_bpe using gist(geom);
# ALTER TABLE fab.insee_bpe add primary key (id);


# DROP TABLE IF EXISTS douaisis.insee_bpe;
# CREATE TABLE douaisis.insee_bpe AS
# 	SELECT * FROM bpe.insee_bpe b
# 		WHERE st_intersects(b.geom,
# 			(SELECT st_transform(st_union(c.geom),2154)
# 				FROM douaisis.communes_etude c));


# CREATE INDEX sidx_insee_bpe_geom on douaisis.insee_bpe using gist(geom);
# ALTER TABLE douaisis.insee_bpe add primary key (id);
