-- Création de la table unités foncières
DROP TABLE IF EXISTS unites_foncieres;
CREATE TABLE unites_foncieres (
    id_uf serial PRIMARY KEY,
    geom GEOMETRY (MULTIPOLYGON, 2154),
    code_insee text,
    idprocpte text,
    catpro text
);

-- Création unités foncières et insertion dans la table
-- Agrégation des géométries par idprocpte, catpro et code_insee
-- puis découpage des multipolygones en polygones simples
-- pour distinguer les différentes unités foncières disjointes
-- d'un même propriétaire sur une même commune (unités foncières non contiguës)
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
ALTER TABLE parcellaire
ADD COLUMN IF NOT EXISTS id_uf integer,
ADD COLUMN IF NOT EXISTS geom_centroid GEOMETRY (POINT, 2154);

UPDATE parcellaire SET geom_centroid = st_pointonsurface(geom);

-- création d'un index spatial sur geom_centroid si n'existe pas
DO $$
DECLARE
  idx_exists boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1
    FROM pg_index i
    JOIN pg_class tbl ON tbl.oid = i.indrelid
    JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
    JOIN pg_class idx ON idx.oid = i.indexrelid
    JOIN pg_am am ON am.oid = idx.relam
    JOIN LATERAL (
      SELECT array_agg(att.attname ORDER BY ord) AS cols  -- name[]
      FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord)
      JOIN pg_attribute att
        ON att.attrelid = tbl.oid AND att.attnum = k.attnum
    ) c ON true
    WHERE ns.nspname = 'public'
      AND tbl.relname = 'parcellaire'
      AND am.amname = 'gist'
      AND c.cols = ARRAY['geom_centroid']::name[]
      AND i.indpred IS NULL      -- pas d’index partiel
      AND i.indexprs IS NULL     -- pas d’index d’expression
  ) INTO idx_exists;

  IF NOT idx_exists THEN
    EXECUTE 'CREATE INDEX parcellaire_geom_centroid_sidx
             ON public.parcellaire USING gist (geom_centroid)';
  END IF;
END
$$;

-- mise à jour de la table parcellaire avec id_uf
-- utilisation de l'index spatial sur geom_centroid
-- pour améliorer les performances
UPDATE parcellaire p SET id_uf = uf.id_uf
FROM unites_foncieres AS uf
WHERE
    p.id_uf IS null
    AND uf.geom && p.geom_centroid
    AND st_intersects(p.geom_centroid, uf.geom);

-- Agrégation des données de la table parcellaire vers la table unités foncières
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
ADD COLUMN catpro_niv2 text,
ADD COLUMN presgdprop text,
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
    catpro = a.catpro,
    catpro_niv2 = a.catpro_niv2,
    presgdprop = a.presgdprop,
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
        max(coalesce(catpro, '')) AS catpro,
        max(coalesce(catpro_niv2, '')) AS catpro_niv2,
        max(coalesce(presgdprop, '')) AS presgdprop,
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


-- création d'un index spatial sur la table unités foncières
CREATE INDEX IF NOT EXISTS unites_foncieres_geom_sidx
ON unites_foncieres USING gist (geom);