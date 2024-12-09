--
-- Name: cadastre_bati; Type: TABLE; Schema: public; Owner: spreadsheep_ids
--
DROP TABLE IF EXISTS cadastre_bati CASCADE;
CREATE TABLE cadastre_bati (
    ogc_fid integer NOT NULL,
    wkb_geometry geometry(MultiPolygon,4326),
    type character varying,
    nom character varying,
    commune character varying,
    created character varying,
    updated character varying
);


--
-- Name: cadastre_bati_ogc_fid_seq; Type: SEQUENCE; Schema: public; Owner: spreadsheep_ids
--

CREATE SEQUENCE cadastre_bati_ogc_fid_seq
    -- AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cadastre_bati_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spreadsheep_ids
--

ALTER SEQUENCE cadastre_bati_ogc_fid_seq OWNED BY cadastre_bati.ogc_fid;


--
-- Name: cadastre_bati ogc_fid; Type: DEFAULT; Schema: public; Owner: spreadsheep_ids
--

ALTER TABLE ONLY cadastre_bati ALTER COLUMN ogc_fid SET DEFAULT nextval('cadastre_bati_ogc_fid_seq'::regclass);


--
-- Name: cadastre_bati cadastre_bati_pkey; Type: CONSTRAINT; Schema: public; Owner: spreadsheep_ids
--

ALTER TABLE ONLY cadastre_bati
    ADD CONSTRAINT cadastre_bati_pkey PRIMARY KEY (ogc_fid);


--
-- Name: cadastre_bati_geom_idx; Type: INDEX; Schema: public; Owner: spreadsheep_ids
--

CREATE INDEX cadastre_bati_geom_idx ON cadastre_bati USING gist (wkb_geometry);
