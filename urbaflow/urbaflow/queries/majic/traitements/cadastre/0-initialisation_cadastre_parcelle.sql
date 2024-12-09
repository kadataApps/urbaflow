DROP TABLE IF EXISTS cadastre_parcelles CASCADE;
--
-- Name: cadastre_parcelles; Type: TABLE; Schema: public; Owner: spreadsheep_ids
--

CREATE TABLE cadastre_parcelles (
    ogc_fid integer NOT NULL,
    wkb_geometry geometry(Multipolygon,2154),
    id character varying,
    commune character varying,
    prefixe character varying,
    section character varying,
    numero character varying,
    contenance integer,
    arpente integer,
    created character varying,
    updated character varying
);


--
-- Name: cadastre_parcelles_ogc_fid_seq; Type: SEQUENCE; Schema: public; Owner: spreadsheep_ids
--
DROP SEQUENCE IF EXISTS cadastre_parcelles_ogc_fid_seq;
CREATE SEQUENCE cadastre_parcelles_ogc_fid_seq
    -- AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cadastre_parcelles ogc_fid; Type: DEFAULT; Schema: public; Owner: spreadsheep_ids
--

ALTER TABLE ONLY cadastre_parcelles ALTER COLUMN ogc_fid SET DEFAULT nextval('cadastre_parcelles_ogc_fid_seq'::regclass);


--
-- Name: cadastre_parcelles cadastre_parcelles_pkey; Type: CONSTRAINT; Schema: public; Owner: spreadsheep_ids
--

ALTER TABLE ONLY cadastre_parcelles
    ADD CONSTRAINT cadastre_parcelles_pkey PRIMARY KEY (ogc_fid);


--
-- Name: cadastre_parcelles_geom_idx; Type: INDEX; Schema: public; Owner: spreadsheep_ids
--

CREATE INDEX cadastre_parcelles_geom_idx ON cadastre_parcelles USING gist (wkb_geometry);
