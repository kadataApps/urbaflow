-- noqa: disable=CP03
DROP TABLE IF EXISTS ilots;
-- CREATE TABLE ilots AS 

-- WITH u AS (
--   SELECT code_insee,
--          (ST_Dump(ST_UnaryUnion(ST_Collect(geom)))).geom AS geom
--   FROM unites_foncieres
--   GROUP BY code_insee
-- )
-- SELECT
--   code_insee,
--   ROW_NUMBER() OVER (PARTITION BY code_insee 
--     ORDER BY ST_Area(geom) DESC) AS comp_id,
--   st_multi(geom)::geometry(MULTIPOLYGON,2154)
-- FROM u;

CREATE TABLE IF NOT EXISTS ilots AS
WITH by_insee AS (
    SELECT
        code_insee,
        array_agg(geom) AS geoms
    FROM unites_foncieres
    GROUP BY code_insee
),

clusters AS (  -- regroupe par contiguïté stricte (touche/intersecte)
    SELECT
        code_insee,
        unnest(ST_ClusterIntersecting(geoms)) AS geoms
    FROM by_insee
),

members AS (   -- remet chaque polygone de cluster en lignes
    SELECT
        code_insee,
        row_number() OVER (PARTITION BY code_insee) AS cid,
        (ST_Dump(geoms)).geom AS geom
    FROM clusters
),

diss AS (      -- dissout à l’intérieur de chaque cluster
    SELECT
        code_insee,
        cid,
        ST_UnaryUnion(ST_Collect(geom)) AS geom
    FROM members
    GROUP BY code_insee, cid
),

parts AS (     -- DUMP après union (au cas où) et force MULTIPOLYGON
    SELECT
        code_insee,
        cid,
        (ST_Dump(geom)).geom AS geom
    FROM diss
)

SELECT
    code_insee,
    cid,
    ST_Multi(geom)::GEOMETRY (MULTIPOLYGON, 2154) AS geom
FROM parts;

CREATE INDEX sidx_ilots ON ilots USING gist (geom);
CREATE INDEX idx_ilots_insee ON ilots (code_insee);
ANALYZE ilots;



CREATE TABLE ilots_decoupes AS
WITH inter AS (
    SELECT
        i.code_insee,
        i.cid,
        z.libelle,
        i.geom AS geom_ilot,
        z.geom AS geom_zone,
        ST_CollectionExtract(ST_Intersection(i.geom, z.geom), 3) AS geom_inter
    FROM ilots AS i
    INNER JOIN urba_zone_urba AS z
        ON ST_Intersects(i.geom, z.geom)
)

SELECT
    code_insee,
    cid,
    libelle,
    ST_Multi(geom_inter)::GEOMETRY (MULTIPOLYGON, 2154) AS geom,
    ST_Area(geom_inter) AS area_m2,
    ST_Area(geom_ilot) AS ilot_area_m2,
    CASE
        WHEN ST_Area(geom_ilot) > 0
            THEN ST_Area(geom_inter) / ST_Area(geom_ilot)
    END AS ratio_ilot
FROM inter
WHERE geom_inter IS NOT NULL AND NOT ST_IsEmpty(geom_inter);

CREATE INDEX ilots_decoupes_gix ON ilots_decoupes USING gist (geom);
ANALYZE ilots_decoupes;


ALTER TABLE ilots_decoupes ADD COLUMN id_ilot SERIAL PRIMARY KEY;
