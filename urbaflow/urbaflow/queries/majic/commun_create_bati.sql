--
-- Name: bati_france; Type: TABLE; Schema: public; Owner: spreadsheep_ids
--

CREATE TABLE public.bati_france (
    ogc_fid integer NOT NULL,
    wkb_geometry public.geometry(MultiPolygon,4326),
    type character varying,
    nom character varying,
    code_insee character varying,
    created character varying,
    updated character varying
);


--
-- Name: bati_france_ogc_fid_seq; Type: SEQUENCE; Schema: public; Owner: spreadsheep_ids
--

CREATE SEQUENCE public.bati_france_ogc_fid_seq
   -- AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bati_france_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spreadsheep_ids
--

ALTER SEQUENCE public.bati_france_ogc_fid_seq OWNED BY public.bati_france.ogc_fid;


--
-- Name: bati_france ogc_fid; Type: DEFAULT; Schema: public; Owner: spreadsheep_ids
--

ALTER TABLE ONLY public.bati_france ALTER COLUMN ogc_fid SET DEFAULT nextval('public.bati_france_ogc_fid_seq'::regclass);


--
-- Name: bati_france bati_france_pkey; Type: CONSTRAINT; Schema: public; Owner: spreadsheep_ids
--

ALTER TABLE ONLY public.bati_france
    ADD CONSTRAINT bati_france_pkey PRIMARY KEY (ogc_fid);


--
-- Name: bati_france_geom_idx; Type: INDEX; Schema: public; Owner: spreadsheep_ids
--

CREATE INDEX bati_france_geom_idx ON public.bati_france USING gist (wkb_geometry);
