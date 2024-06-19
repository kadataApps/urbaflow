SET SEARCH_PATH to public;
UPDATE parcellaire_douaisis set geom = polygonalmakevalid(geom) where st_isvalid(geom) is false;

-- Création de la table unités foncières

CREATE TABLE unites_foncieres  (
  id_uf serial PRIMARY KEY, 
  geom geometry(MULTIPOLYGON, 2154),
  code_insee text,
  idprocpte text,
  catpro text
  );

-- Création unités foncières ----
INSERT INTO unites_foncieres (geom, idprocpte, catpro, code_insee )
  SELECT st_multi((st_dump(geom)).geom) geom, idprocpte, catpro, code_insee
    FROM (
      SELECT idprocpte, catpro, code_insee, st_union(geom) geom 
        FROM parcellaire_douaisis
        GROUP BY 1, 2, 3
    ) t;



-- modification de la table parcelle
ALTER TABLE parcellaire_douaisis ADD COLUMN id_uf integer;
ALTER TABLE parcellaire_douaisis ADD COLUMN centroid_geom geometry(POINT, 2154);
UPDATE parcellaire_douaisis SET centroid_geom = st_pointonsurface(geom);
CREATE INDEX parcellaire_douaisis_centroid_geom_sidx on parcellaire_douaisis using gist(centroid_geom);


UPDATE  parcellaire_douaisis p SET id_uf = uf.id_uf
  FROM  unites_foncieres uf
  WHERE p.id_uf is null AND uf.geom && p.centroid_geom AND st_intersects(p.centroid_geom, uf.geom);


ALTER TABLE unites_foncieres 
  ADD COLUMN dcntpa integer, 
  ADD COLUMN nbat integer, 
  ADD COLUMN nlocal integer, 
  ADD COLUMN spevtot integer, 
  ADD COLUMN nloclog integer, 
  ADD COLUMN nloccom integer, 
  ADD COLUMN nloccomsec integer, 
  ADD COLUMN nloccomter integer, 
  ADD COLUMN nlogh integer, 
  ADD COLUMN nloghvac integer, 
  ADD COLUMN nloghpp integer, 
  ADD COLUMN nloghlm integer, 
  ADD COLUMN ndroit integer, 
  ADD COLUMN descprop text, 
  ADD COLUMN ndroitpro integer, 
  ADD COLUMN ndroitges integer, 
  ADD COLUMN typprop text, 
  ADD COLUMN typproppro text, 
  ADD COLUMN typpropges text, 
  ADD COLUMN ddenomprop text, 
  ADD COLUMN ddenomproppro text, 
  ADD COLUMN ddenompropges text,
  ADD COLUMN dcntarti integer,
  ADD COLUMN dcntnaf integer,
  ADD COLUMN jannatmin integer,
  ADD COLUMN jannatmax integer,
  ADD COLUMN jdatatan integer,
  ADD COLUMN ncp integer
  ;

UPDATE unites_foncieres SET 
  dcntpa = a.dcntpa,
  nbat = a.nbat,
  nlocal = a.nlocal,
  spevtot = a.spevtot,
  nloclog = a.nloclog,
  nloccom = a.nloccom,
  nloccomsec = a.nloccomsec,
  nloccomter = a.nloccomter,
  nlogh = a.nlogh,
  nloghvac = a.nloghvac,
  nloghpp = a.nloghpp,
  nloghlm = a.nloghlm,
  ndroit = a.ndroit,
  descprop = a.descprop,
  ndroitpro = a.ndroitpro,
  ndroitges = a.ndroitges,
  typprop = a.typprop,
  typproppro = a.typproppro,
  typpropges = a.typpropges,
  ddenomprop = a.ddenomprop,
  ddenomproppro = a.ddenomproppro,
  ddenompropges = a.ddenompropges,
  dcntarti = a.dcntarti,
  dcntnaf = a.dcntnaf,
  jannatmin = a.jannatmin,
  jannatmax = a.jannatmax,
  jdatatan = a.jdatatan,
  ncp = a.ncp

  FROM (
    SELECT p.id_uf, 
      sum(coalesce(dcntpa,0)) as dcntpa,
      sum(coalesce(nbat,0)) as nbat,
      sum(coalesce(nlocal,0)) as nlocal,
      sum(coalesce(spevtot,0)) as spevtot,
      sum(coalesce(nloclog,0)) as nloclog,
      sum(coalesce(nloccom,0)) as nloccom,
      sum(coalesce(nloccomsec,0)) as nloccomsec,
      sum(coalesce(nloccomter,0)) as nloccomter,
      sum(coalesce(nlogh,0)) as nlogh,
      sum(coalesce(nloghvac,0)) as nloghvac,
      sum(coalesce(nloghpp,0)) as nloghpp,
      sum(coalesce(nloghlm,0)) as nloghlm,
      sum(coalesce(ndroit,0)) as ndroit,
      max(coalesce(descprop,'')) as descprop,
      max(coalesce(ndroitpro,0)) as ndroitpro,
      max(coalesce(ndroitges,0)) as ndroitges,
      max(coalesce(typprop,'')) as typprop,
      max(coalesce(typproppro,'')) as typproppro,
      max(coalesce(typpropges,'')) as typpropges,
      max(coalesce(ddenomprop,'')) as ddenomprop,
      max(coalesce(ddenomproppro,'')) as ddenomproppro,
      max(coalesce(ddenompropges,'')) as ddenompropges,
      sum(coalesce(dcntarti,'')) as dcntarti,
      sum(coalesce(dcntnaf,'')) as dcntnaf,
      min(coalesce(jannatmin,'')) as jannatmin,
      max(coalesce(jannatmax,'')) as jannatmax,
      max(coalesce(jdatatan,'')) as jdatatan,
      max(coalesce(ncp,'')) as ncp
    FROM parcellaire_douaisis p
    GROUP BY id_uf

  ) a
  WHERE a.id_uf = unites_foncieres.id_uf;