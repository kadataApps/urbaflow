-- Table: public.proprietaire_droit;

-- DROP TABLE public.proprietaire_droit;

CREATE TABLE IF NOT EXISTS public.proprietaire_droit (
    -- Computed fields are marked with *
    -- Numbering is the one as from CEREMA
    -- Fields without numbers are additional fields
    -- http://doc-datafoncier.cerema.fr/ff/doc_fftp/table/proprietaire_droit/last/ --noqa
    --                      # Mod Comment
    proprietaire text,   --
    annee text,          --
    idprodroit char(13), -- 1  *
    idprocpte char(11),  -- 2  *
    idpersonne char(8),  -- 3  *
    idvoie char(9),      -- 4  *
    idcom char(5),       -- 5  *
    idcomtxt char(45),   -- 6  *
    ccodep char(2),      -- 7
    ccodir char(1),      -- 8
    ccocom char(3),      -- 9
    dnupro char(6),      -- 10
    comptecommunal text, --
    dnulp char(2),       -- 11
    ccocif char(4),      -- 12
    dnuper char(6),      -- 13
    ccodro char(1),      -- 14
    ccodrotxt char(88),  -- 15 *
    typedroit char(1),   -- 16
    ccodem char(1),      -- 17
                         -- 18   missing ccodemtxt --noqa
    gdesip char(1),      -- 19
    gtoper char(1),      -- 20
    ccoqua char(1),      -- 21
    gnexcf text,         --
    dtaucf text,         --
    dnatpr char(3),      -- 22
    dnatprtxt char(53),  -- 23 *
    ccogrm char(2),      -- 24
    ccogrmtxt text,      -- 25
    codgrm text,         -- *
    codgrmtxt text,      -- *
    -- codgrm : ccogrm est souvent mal renseignée. Le Cerema Nord-Picardie a
    -- donc fiabilisé cette donnée en s’inspirant de ce classement mais en
    -- repartant des noms des propriétaires
    -- http://doc-datafoncier.cerema.fr/static/fiches/fiche_18.pdf

    dsglpm char(10),     -- 26
    dforme char(7),      -- 27
    ddenom char(60),     -- 28
    gtyp3 char(1),       -- 29
    gtyp4 char(1),       -- 30
    gtyp5 char(1),       -- 31
    gtyp6 char(1),       -- 32
    dlign3 char(30),     -- 33
    dlign4 char(36),     -- 34
    dlign5 char(30),     -- 35
    dlign6 char(32),     -- 36
    ccopay char(3),      -- 37
    ccodep1a2 char(2),   -- 38
    ccodira char(1),     -- 39

    ccocomadr char(3),   -- 41
    ccovoi char(5),      -- 42
    ccoriv char(5),      -- 43
    dnvoiri char(4),     -- 44
    dindic char(1),      -- 45
    ccopos char(5),      -- 46
    dnirpp text,         --
    dqualp char(3),      -- 47
    dnomlp char(30),     -- 48
    dprnlp char(15),     -- 49
    jdatnss char(10),    -- 50
    dldnss char(58),     -- 51
    epxnee text,         --
    dnomcp text,         --
    dprncp text,         --
    topcdi text,         --
    oriard text,         --
    fixard text,         --
    datadr text,         --
    topdec text,         --
    datdec text,         --
    dsiren char(10),     -- 55
    ccmm text,           --
    topja char(1),       -- 56
    datja char(8),       -- 57
    anospi text,         --
    cblpmo text,         --
    gtodge text,         --
    gpctf text,          --
    gpctsb text,         --
    jmodge text,         --
    jandge text,         --
    jantfc text,         --
    jantbc text,         --
    dformjur char(4),    -- 58
    dnomus char(60),     -- 59
    dprnus char(40),     -- 60
    lot text,            --
    locprop char(1),     -- 61 *
    locproptxt char(21), -- 62 *
    codnom text,         --
    catpro text,      --
    catpro_niv2 text, --
    nlogh integer,       --
    nloghvac integer,    --
    nloghpp integer,     --
    nloghmeu integer,    --
    nloghloue integer,    --
    nloghautre integer,  --
    nloghnonh integer,   --
    nloghlm integer,     --
    gdprop char(1)       --
) WITH (
    oids = FALSE
)
TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS sidx_proprietaire_droit
ON public.proprietaire_droit (idprocpte)
TABLESPACE pg_default;
