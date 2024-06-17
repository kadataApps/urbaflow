-- Table: public.parcellaire_france

-- DROP TABLE public.parcellaire_france;

CREATE TABLE public.parcellaire_france (
    geom geometry(MultiPolygon, 2154),                          --
    idparcelle_geom text COLLATE pg_catalog."default" NOT NULL, --
    code_insee character varying COLLATE pg_catalog."default",  --
    idpar text COLLATE pg_catalog."default",                    -- 1
    idpar_simple text COLLATE pg_catalog."default",             -- 
    idprocpte text COLLATE pg_catalog."default",                -- 4
    dcntpa integer,                                             -- 16
    jdatat char(8),                                             -- 19
    libcom text COLLATE pg_catalog."default",                   --
    dlibvoi text COLLATE pg_catalog."default",                  --
    adressepar text COLLATE pg_catalog."default",               --
    jdatatan integer,                                           -- 48
    jannatmin integer,                                          -- 49
    jannatmax integer,                                          -- 50
    jannatminh integer,                                         -- 51
    jannatmaxh integer,                                         -- 52
    dcntarti integer,                                           -- 59
    dcntnaf integer,                                            -- 60
    nbat numeric,                                               -- 93
    nlocal numeric,                                             -- 79
    spevtot numeric,                                            --
    nloclog numeric,                                            -- 83
    nloccom numeric,                                            -- 84
    nloccomsec numeric,                                         -- 89
    nloccomter numeric,                                         -- 86
    nlogh numeric,                                              -- 96
    nloghvac numeric,                                           -- 104
    nloghpp numeric,                                            -- 107
    nloghlm numeric,                                            -- 118
    ncp smallint,                                               -- 131
    ndroit numeric,                                             -- 146
    descprop text COLLATE pg_catalog."default",                 --
    ndroitpro numeric,                                          -- 148
    ndroitges numeric,                                          -- 149
    ndroitpro_parcelle_bati numeric,                            --
    typprop text COLLATE pg_catalog."default",                  --
    typproppro text COLLATE pg_catalog."default",               --
    typpropges text COLLATE pg_catalog."default",               --
    typproprietaire text COLLATE pg_catalog."default",          --
    typproprietaire_niv2 text COLLATE pg_catalog."default",     --
    ddenomprop text COLLATE pg_catalog."default",               --
    ddenomproppro text COLLATE pg_catalog."default",            --
    ddenompropges text COLLATE pg_catalog."default",            --
    CONSTRAINT parcellaire_france_pkey PRIMARY KEY (idparcelle_geom)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

CREATE INDEX sidx_parcellaire_france
    ON public.parcellaire_france
    USING gist(geom)
TABLESPACE pg_default;
