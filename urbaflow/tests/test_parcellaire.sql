\set ON_ERROR_STOP on

BEGIN;
CREATE SCHEMA test_parcellaire;
SET LOCAL search_path TO test_parcellaire, public;

CREATE TABLE cadastre_parcelles (
    geo_parcelle text,
    commune text,
    prefixe text,
    section text,
    numero text,
    wkb_geometry geometry
);

CREATE TABLE parcelle (
    parcelle text,
    ccodir text,
    ccopre text,
    dnupla text,
    dnupro text,
    comptecommunal text,
    dcntpa integer,
    gpdl text,
    dnupdl text,
    cprsecr text,
    ccosecr text,
    dnuplar text,
    dparpi text,
    gparnf text,
    gparbat text,
    dnvoiri text,
    dindic text,
    ccoriv text,
    cconvo text,
    jdatat text,
    ccodep text,
    ccocom text
);

INSERT INTO cadastre_parcelles
SELECT
    'parcelle_' || row_number() OVER (),
    '33063', '000', 'AB', '0001',
    st_geomfromewkt(geometry_text)
FROM (VALUES
    ('SRID=4326;POLYGON((0 45, 0.01 45, 0.01 45.01, 0 45.01, 0 45))'),
    ('SRID=4326;MULTIPOLYGON(((0 45, 0.01 45, 0.01 45.01, 0 45.01, 0 45)))'),
    ('SRID=4326;POLYGON((0 45, 0.01 45.01, 0.01 45, 0 45.01, 0 45))'),
    ('SRID=4326;GEOMETRYCOLLECTION(POLYGON((0 45, 0.01 45, 0.01 45.01, 0 45.01, 0 45)),LINESTRING(0 45, 0.01 45))'),
    ('SRID=4326;POLYGON Z((0 45 5, 0.01 45 5, 0.01 45.01 5, 0 45.01 5, 0 45 5))'),
    ('SRID=2154;POLYGON((700000 6600000, 700100 6600000, 700100 6600100, 700000 6600100, 700000 6600000))'),
    ('SRID=4326;POLYGON EMPTY'),
    ('SRID=2154;POLYGON((700000 6600000, 700100 6600000, 700200 6600000, 700000 6600000))'),
    (NULL)
) AS geometries(geometry_text);

INSERT INTO parcelle (parcelle, dnupro, ccodep, ccocom)
VALUES ('parcelle_1', '00001', '33', '063');

\ir ../urbaflow/queries/majic/traitements/merge/0-creation_table_parcellaire.sql

DO $$
DECLARE
    primary_key_columns text[];
BEGIN
    IF (SELECT count(*) FROM parcellaire) <> 9 THEN
        RAISE EXCEPTION 'Des parcelles ont été perdues pendant la fusion';
    END IF;

    IF EXISTS (
        SELECT 1 FROM parcellaire
        WHERE geom IS NOT NULL AND (
            NOT st_isvalid(geom)
            OR geometrytype(geom) <> 'MULTIPOLYGON'
            OR st_srid(geom) <> 2154
            OR st_ndims(geom) <> 2
        )
    ) THEN
        RAISE EXCEPTION 'Les géométries ne respectent pas le contrat attendu';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM geometry_columns
        WHERE f_table_schema = 'test_parcellaire'
            AND f_table_name = 'parcellaire'
            AND f_geometry_column = 'geom'
            AND type = 'MULTIPOLYGON' AND srid = 2154 AND coord_dimension = 2
    ) THEN
        RAISE EXCEPTION 'Le type de la colonne géométrique est incorrect';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM parcellaire AS result
        JOIN cadastre_parcelles AS source
            ON result.idparcelle_geom = source.geo_parcelle
        WHERE result.idparcelle_geom = 'parcelle_1'
            AND st_equals(result.geom, st_transform(source.wkb_geometry, 2154))
            AND result.idprocpte = '3306300001'
    ) OR NOT EXISTS (
        SELECT 1 FROM parcellaire AS result
        JOIN cadastre_parcelles AS source
            ON result.idparcelle_geom = source.geo_parcelle
        WHERE result.idparcelle_geom = 'parcelle_6'
            AND st_equals(result.geom, source.wkb_geometry)
            AND result.idprocpte IS NULL
    ) THEN
        RAISE EXCEPTION 'La projection ou la jointure MAJIC a changé';
    END IF;

    IF (SELECT count(*) FROM parcellaire WHERE st_isempty(geom)) <> 2
        OR (SELECT count(*) FROM parcellaire WHERE geom IS NULL) <> 1
        OR NOT EXISTS (
            SELECT 1 FROM parcellaire
            WHERE idparcelle_geom = 'parcelle_3' AND st_numgeometries(geom) = 2
        )
    THEN
        RAISE EXCEPTION 'La réparation des géométries est incorrecte';
    END IF;

    SELECT array_agg(attribute.attname::text ORDER BY key.ordinality)
    INTO primary_key_columns
    FROM pg_constraint AS constraint_info
    CROSS JOIN LATERAL unnest(constraint_info.conkey)
        WITH ORDINALITY AS key(attribute_number, ordinality)
    JOIN pg_attribute AS attribute
        ON attribute.attrelid = constraint_info.conrelid
            AND attribute.attnum = key.attribute_number
    WHERE constraint_info.conrelid = 'parcellaire'::regclass
        AND constraint_info.contype = 'p';

    IF primary_key_columns IS DISTINCT FROM ARRAY['idparcelle_geom'] THEN
        RAISE EXCEPTION 'La clé primaire cadastrale est absente';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'test_parcellaire' AND tablename = 'parcellaire'
            AND indexdef LIKE '%USING gist (geom)'
    ) OR (
        SELECT count(*) FROM pg_indexes
        WHERE schemaname = 'test_parcellaire' AND tablename = 'parcellaire'
            AND indexname IN ('parcelle_idprocpte_idx', 'parcelle_idpar_idx')
    ) <> 2 THEN
        RAISE EXCEPTION 'Les index attendus sont absents';
    END IF;

    BEGIN
        INSERT INTO parcellaire (idparcelle_geom) VALUES ('parcelle_1');
        RAISE EXCEPTION 'Un identifiant dupliqué a été accepté';
    EXCEPTION WHEN unique_violation THEN
        NULL;
    END;

    BEGIN
        INSERT INTO parcellaire (idparcelle_geom) VALUES (NULL);
        RAISE EXCEPTION 'Un identifiant nul a été accepté';
    EXCEPTION WHEN not_null_violation THEN
        NULL;
    END;

    BEGIN
        UPDATE parcellaire
        SET geom = st_geomfromewkt(
            'SRID=2154;MULTIPOLYGON(((0 0, 1 1, 1 0, 0 1, 0 0)))'
        ) WHERE idparcelle_geom = 'parcelle_1';
        RAISE EXCEPTION 'Une géométrie invalide a été acceptée';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;

    BEGIN
        UPDATE parcellaire
        SET geom = st_geomfromewkt('SRID=2154;POINT(700000 6600000)')
        WHERE idparcelle_geom = 'parcelle_1';
        RAISE EXCEPTION 'Un type géométrique incorrect a été accepté';
    EXCEPTION WHEN invalid_parameter_value THEN
        NULL;
    END;

    BEGIN
        UPDATE parcellaire
        SET geom = st_geomfromewkt('SRID=4326;MULTIPOLYGON EMPTY')
        WHERE idparcelle_geom = 'parcelle_1';
        RAISE EXCEPTION 'Un SRID incorrect a été accepté';
    EXCEPTION WHEN invalid_parameter_value THEN
        NULL;
    END;
END
$$;

ROLLBACK;
