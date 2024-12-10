--
-- Name: bati_france; Type: TABLE; Schema: public; Owner: spreadsheep_ids
--

CREATE TABLE IF NOT EXISTS public.bati_france (
    ogc_fid serial PRIMARY KEY,
    wkb_geometry public.geometry(MultiPolygon,4326),
    type character varying,
    nom character varying,
    code_insee character varying,
    created character varying,
    updated character varying
);



CREATE INDEX IF NOT EXISTS bati_france_geom_idx ON public.bati_france USING gist (wkb_geometry);
