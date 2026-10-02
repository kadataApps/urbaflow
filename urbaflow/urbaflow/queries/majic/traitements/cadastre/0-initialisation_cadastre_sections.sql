DROP TABLE IF EXISTS cadastre_sections CASCADE;

CREATE TABLE cadastre_sections (
    ogc_fid serial PRIMARY KEY,
    wkb_geometry GEOMETRY (MULTIPOLYGON, 4326),
    id character varying,
    commune character varying,
    prefixe character varying,
    code character varying,
    created character varying,
    updated character varying
);

CREATE INDEX cadastre_sections_geom_idx
ON cadastre_sections USING gist (wkb_geometry);
