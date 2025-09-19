-- noqa: disable=CP03
-- Affectation d'un identifiant d'ilot (id_ilot)
-- aux batiments issues de la BD Topo

ALTER TABLE bdtopo_batiment
ADD COLUMN IF NOT EXISTS id_ilot INTEGER,
ADD COLUMN IF NOT EXISTS geom_centroid GEOMETRY (POINT, 2154);

UPDATE bdtopo_batiment
SET geom_centroid = ST_pointOnSurface(geom);

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
      AND tbl.relname = 'bdtopo_batiment'
      AND am.amname = 'gist'
      AND c.cols = ARRAY['geom_centroid']::name[]
      AND i.indpred IS NULL      -- pas d’index partiel
      AND i.indexprs IS NULL     -- pas d’index d’expression
  ) INTO idx_exists;

  IF NOT idx_exists THEN
    EXECUTE 'CREATE INDEX bdtopo_batiment_geom_centroid_sidx
             ON public.bdtopo_batiment USING gist (geom_centroid)';
  END IF;
END
$$;

-- Affectation de l'id_ilot aux batiments
UPDATE bdtopo_batiment AS b
SET id_ilot = uf.id_ilot
FROM ilots_decoupes AS uf
WHERE
    uf.geom && b.geom_centroid
    AND ST_Within(b.geom_centroid, uf.geom)
    AND b.id_ilot IS DISTINCT FROM uf.id_ilot;


ALTER TABLE ilots_decoupes
ADD COLUMN IF NOT EXISTS nb_batiments INTEGER,
ADD COLUMN IF NOT EXISTS emprise_batiments_m2 NUMERIC,
ADD COLUMN IF NOT EXISTS sp_estimee_m2 NUMERIC,
ADD COLUMN IF NOT EXISTS ces NUMERIC,
ADD COLUMN IF NOT EXISTS cos NUMERIC,
ADD COLUMN IF NOT EXISTS nb_logts INTEGER,
ADD COLUMN IF NOT EXISTS nb_logts_ha NUMERIC;

COMMENT ON COLUMN ilots_decoupes.nb_batiments
IS 'Nombre de batiments dans l''ilot (source: BD Topo)';
COMMENT ON COLUMN ilots_decoupes.emprise_batiments_m2
IS 'Emprise totale des batiments dans l''ilot (en m²)
 (source: BD Topo)';
COMMENT ON COLUMN ilots_decoupes.sp_estimee_m2
IS 'Surface de plancher estimée des batiments dans l''ilot (en m²)
 (source: BD Topo)';
COMMENT ON COLUMN ilots_decoupes.ces
IS 'Coefficient d''emprise au sol des batiments dans l''ilot (source: BD Topo)';
COMMENT ON COLUMN ilots_decoupes.cos
IS 'Coefficient d''occupation des sols des batiments dans l''ilot
 (source: BD Topo)';
COMMENT ON COLUMN ilots_decoupes.nb_logts
IS 'Nombre de logements dans l''ilot (source: BD Topo)';
COMMENT ON COLUMN ilots_decoupes.nb_logts_ha
IS 'Densité de logements dans l''ilot (nombre de logements par hectare)
 (source: BD Topo)';

UPDATE ilots_decoupes ilots
SET
    nb_batiments = sub.nb_batiments,
    emprise_batiments_m2 = sub.emprise_batiments_m2,
    sp_estimee_m2 = sub.sp_estimee_m2,
    ces = sub.emprise_batiments_m2 / nullif(ST_Area(ilots.geom), 0),
    cos = sub.sp_estimee_m2 / nullif(ST_Area(ilots.geom), 0),
    nb_logts = sub.nb_logts,
    nb_logts_ha = sub.nb_logts / nullif(ST_Area(ilots.geom) / 10000, 0)
FROM (
    SELECT
        id_ilot,
        count(*) AS nb_batiments,
        sum(emprise) AS emprise_batiments_m2,
        sum(surface_plancher) AS sp_estimee_m2,
        sum(nb_logts) AS nb_logts
    FROM bdtopo_batiment
    GROUP BY id_ilot
) AS sub
WHERE ilots.id_ilot = sub.id_ilot;


---- Croisement avec les unités foncières pour récupérer des informations
---- sur le nombre de logements et surfaces


ALTER TABLE ilots_decoupes
ADD COLUMN IF NOT EXISTS nb_logts_majic INTEGER,
ADD COLUMN IF NOT EXISTS surface_majic NUMERIC,
ADD COLUMN IF NOT EXISTS nb_logts_ha_majic NUMERIC;

COMMENT ON COLUMN ilots_decoupes.nb_logts_majic
IS 'Nombre de logements dans l''ilot (source: MAJIC)';
COMMENT ON COLUMN ilots_decoupes.surface_majic
IS 'Surface de plancher dans l''ilot (en m²)
 - tout type d''affectation (source: MAJIC)';
COMMENT ON COLUMN ilots_decoupes.nb_logts_ha_majic
IS 'Densité de logements dans l''ilot 
(nombre de logements par hectare) (source: MAJIC)';

UPDATE ilots_decoupes ilots
SET
    nb_logts_majic = sub.nb_logts_majic,
    surface_majic = sub.surface_majic,
    nb_logts_ha_majic
    = sub.nb_logts_majic / nullif(ST_Area(ilots.geom) / 10000, 0)
FROM (
    SELECT
        i.id_ilot,
        sum(u.spevtot) AS surface_majic,
        sum(u.logh) AS nb_logts_majic
    FROM unites_foncieres AS u INNER JOIN ilots_decoupes AS i
        ON ST_Intersects(st_pointonsurface(u.geom), i.geom)
    GROUP BY i.id_ilot
) AS sub
WHERE ilots.id_ilot = sub.id_ilot;
