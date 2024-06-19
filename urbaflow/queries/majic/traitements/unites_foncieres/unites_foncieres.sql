-- Création unités foncières

CREATE TABLE unites_foncieres (
  id_uf serial,
  geom geometry(MULTIPOLYGON, 2154),
  idprocpte text,
  catpro text
  );
ALTER TABLE unites_foncieres ADD PRIMARY KEY (id_uf);

INSERT INTO unites_foncieres (geom, idprocpte )
  SELECT (st_dump(geom)).geom geom, idprocpte
      FROM (SELECT idprocpte, st_union(geom) geom FROM parcellaire GROUP BY 1) t;