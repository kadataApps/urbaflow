SET SEARCH_PATH TO saintes, public;
UPDATE parcellaire SET geom = polygonalmakevalid(geom)
WHERE st_isvalid(geom) IS false;

-- Création de la table unités foncières

CREATE TABLE unites_foncieres (
    id_uf serial PRIMARY KEY,
    geom GEOMETRY (MULTIPOLYGON, 2154),
    code_insee text,
    idprocpte text,
    catpro text
);

-- Création unités foncières ----
INSERT INTO unites_foncieres (geom, idprocpte, catpro, code_insee)
SELECT
    st_multi((st_dump(geom)).geom) AS geom,
    idprocpte,
    catpro,
    code_insee
FROM (
    SELECT
        idprocpte,
        catpro,
        code_insee,
        st_union(geom) AS geom
    FROM parcellaire
    GROUP BY 1, 2, 3
) AS t;



-- modification de la table parcelle
ALTER TABLE parcellaire ADD COLUMN id_uf integer;
ALTER TABLE parcellaire ADD COLUMN centroid_geom GEOMETRY (POINT, 2154);
UPDATE parcellaire SET centroid_geom = st_pointonsurface(geom);
CREATE INDEX parcellaire_centroid_geom_sidx ON parcellaire USING gist (
    centroid_geom
);


UPDATE parcellaire p SET id_uf = uf.id_uf
FROM unites_foncieres AS uf
WHERE
    p.id_uf IS null
    AND uf.geom && p.centroid_geom
    AND st_intersects(p.centroid_geom, uf.geom);


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
ADD COLUMN ncp integer;

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
    SELECT
        p.id_uf,
        sum(coalesce(dcntpa, 0)) AS dcntpa,
        sum(coalesce(nbat, 0)) AS nbat,
        sum(coalesce(nlocal, 0)) AS nlocal,
        sum(coalesce(spevtot, 0)) AS spevtot,
        sum(coalesce(nloclog, 0)) AS nloclog,
        sum(coalesce(nloccom, 0)) AS nloccom,
        sum(coalesce(nloccomsec, 0)) AS nloccomsec,
        sum(coalesce(nloccomter, 0)) AS nloccomter,
        sum(coalesce(nlogh, 0)) AS nlogh,
        sum(coalesce(nloghvac, 0)) AS nloghvac,
        sum(coalesce(nloghpp, 0)) AS nloghpp,
        sum(coalesce(nloghlm, 0)) AS nloghlm,
        sum(coalesce(ndroit, 0)) AS ndroit,
        max(coalesce(descprop, '')) AS descprop,
        max(coalesce(ndroitpro, 0)) AS ndroitpro,
        max(coalesce(ndroitges, 0)) AS ndroitges,
        max(coalesce(typprop, '')) AS typprop,
        max(coalesce(typproppro, '')) AS typproppro,
        max(coalesce(typpropges, '')) AS typpropges,
        max(coalesce(ddenomprop, '')) AS ddenomprop,
        max(coalesce(ddenomproppro, '')) AS ddenomproppro,
        max(coalesce(ddenompropges, '')) AS ddenompropges,
        sum(coalesce(dcntarti, 0)) AS dcntarti,
        sum(coalesce(dcntnaf, 0)) AS dcntnaf,
        min(coalesce(jannatmin, 0)) AS jannatmin,
        max(coalesce(jannatmax, 0)) AS jannatmax,
        max(coalesce(jdatatan, 0)) AS jdatatan,
        max(coalesce(ncp, 0)) AS ncp
    FROM parcellaire AS p
    GROUP BY 1
) AS a
WHERE a.id_uf = unites_foncieres.id_uf;
