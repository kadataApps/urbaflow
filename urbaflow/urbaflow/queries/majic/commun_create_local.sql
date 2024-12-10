-- Table: public.pb0010_local

-- DROP TABLE public.pb0010_local;

CREATE TABLE IF NOT EXISTS public.pb0010_local (
    -- Computed fields are marked with *
    -- Numbering is the one as from CEREMA
    -- Fields without numbers are additional fields
    -- proprietaire_droit
                           -- # Mod Comment
    local10 text,          --
    annee text,            --
    idlocal char(12),      -- 1  *
    idbat char(16),        -- 2  *
    idpar char(14),        -- 3  *
                           -- 4  * Missing idtup
                           -- 5  * Missing idsec
                           -- 6  * Missing idvoie
    idprocpte char(11),    -- 7  *
                           -- 8  * Missing idcom
                           -- 9  * Missing idcomtxt
    ccodep char(2),        -- 10
    ccodir char(1),        -- 11
    ccocom char(3),        -- 12
    invar char(10),        -- 13
    local00 text,          --
    ccopre char(3),        -- 14
    ccosec char(2),        -- 15
    dnupla char(4),        -- 16
    dnubat char(2),        -- 17
                           -- 18   Missing descc
                           -- 19   Missing dniv
                           -- 20   Missing dpor
    parcelle text,         --
    ccoriv char(4),        -- 21
    voie text,             --
    ccovoi char(5),        -- 22
    dnvoiri char(4),       -- 23
                           -- 24   Missing dpor
                           -- 25   Missing ccocif
                           -- 26   Missing dvoilib
                           -- 27   Missing cleinvar
    gpdl char(1),          -- 28
                           -- 29 * Missing ctpdl
                           -- 30   Deprecated
    dsrpar text,           --
    dnupro char(6),        -- 31
    comptecommunal text,   --
    jdatat char(8),        -- 32
                           -- 33 * Missing jdatatv
                           -- 34 * Missing jdatatan
    dnufnl char(6),        -- 35
    ccoeva char(1),        -- 36
                           -- 37 * Missing ccoevatxt
    ccitlv text,           --
    dteloc char(1),        -- 38
                           -- 39 * Missing dteloctxt
    logh char(1),          -- 40 * Missing logh
                           -- 41 * Missing loghmais
                           -- 42 * Missing loghappt
    gtauom char(2),        -- 43
    dcomrd char(3),        -- 44
    ccoplc char(1),        -- 45
                           -- 46 * Missing ccoplctxt
    cconlc char(2),        -- 47
                           -- 48 * Missing cconlctxt
    dvltrt integer,        -- 49
                           -- 50   Deprecated
                           -- 51   Deprecated
    ccoape text,           --      Deprecated since 2011 (see cconac)
    cc48lc char(2),        -- 52
    dloy48a integer,       -- 53
    top48a char(1),        -- 54
    dnatlc char(1),        -- 55
    dnupas text,           --
    gnexcf text,           --
    dtaucf text,           --
                           -- 57 * Missing ccthp
                           -- 58 * Missing proba_rprs
                           -- 59 * Missing typeact
                           -- 61 * Missing actvac
    loghvac char(1),       -- 62 * Missing loghvac
                           -- 65 * Missing actvac2a
                           -- 66 * Missing loghvac2a
                           -- 67 * Missing actvac5a
                           -- 68 * Missing loghvac5a
                           -- 69 * Missing loghvacdeb
    cchpr char(1),         -- 70
    jannat char(4),        -- 71
    dnbniv char(2),        -- 72

    hlmsem char(1),        -- 74

    postel char(1),        -- 76
    dnatcg char(2),        -- 77
    jdatcgl char(8),       -- 78
    dnutbx text,           --
    dvltla text,           --
    janloc text,           --
    ccsloc text,           --
    fburx char(1),         -- 79
    gimtom char(1),        -- 80
    cbtabt char(2),        -- 81
    jdtabt char(4),        --      Deprecated since 2014, see jdbabt
                           -- 83   Missing jdbabt
    jrtabt char(4),        -- 84
    jacloc text,           --
    cconac char(5),        -- 85
                           -- 86 * Missing cconactxt
    toprev char(1),        -- 87
    ccoifp integer,        -- 88
    lot text               --
                           -- 89 * Missing jannath
                           -- 90 * Missing janbilmin
                           -- 91   Deprecated
                           -- 92 * Missing habitat
                           -- 93 * Missing npevph
                           -- 94 * Missing stoth
                           -- 95 * Missing stotdsueic
                           -- 96 * Missing npevd
                           -- 97 * Missing stotd
                           -- 98 * Missing npevp

                           -- 102 * Missing sprincp
                           -- 103 * Missing ssecp
                           -- 104 * Missing ssecncp
                           -- 105 * Missing sparkp
                           -- 106 * Missing sparkncp
                           -- 107 * Missing npevtot

                           -- 109 * Missing slocal
                           -- 110 * Missing npiece_soc
                           -- 111 * Missing npiece_ff
                           -- 112 * Missing npiece_i
                           -- 113 * Missing npiece_p2

                           -- 115 * Missing nbannexe
                           -- 116 * Missing nbgarpark
                           -- 117 * Missing nbagrement
                           -- 118 * Missing nbterrasse
                           -- 119 * Missing nbpiscine
                           -- 120 * Missing ndroit
                           -- 121 * Missing ndroitindi
                           -- 122 * Missing ndroitpro
                           -- 123 * Missing ndroitges

                           -- 130 * Missing catpro2
                           -- 131 * Missing catpro2txt
                           -- 132 * Missing catpro3
                           -- 133 * Missing catpropro2
                           -- 134 * Missing catproges2
                           -- 135 * Missing locprop
                           -- 136 * Missing locproptxt
                           -- 137 * Missing geomloc
                           -- 138 * Missing source_geo
                           -- 139 * Missing vecteur
                           -- 140 * Missing idpk
) WITH (
  OIDS = FALSE
)
TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS sidx_pb0010_local
    ON public.pb0010_local (idlocal)
TABLESPACE pg_default;
