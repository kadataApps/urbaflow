CREATE TABLE IF NOT EXISTS public.sections_cadastrales_france (
    ogc_fid serial PRIMARY KEY,
    wkb_geometry public.GEOMETRY (MULTIPOLYGON, 4326),
    id character varying,
    code_insee character varying,
    prefixe character varying,
    code character varying,
    created character varying,
    updated character varying
);

CREATE INDEX IF NOT EXISTS sections_cadastrales_france_geom_idx
ON public.sections_cadastrales_france USING gist (wkb_geometry);

CREATE UNIQUE INDEX IF NOT EXISTS sections_cadastrales_france_id_idx
ON public.sections_cadastrales_france (id);
