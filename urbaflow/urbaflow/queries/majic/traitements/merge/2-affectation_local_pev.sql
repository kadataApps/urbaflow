-- logh  Logement d’habitation  t = oui, sinon blanc
-- Calculé depuis la table pb21 en prenant dteloc=’1’ ou ‘2’,
-- dnupev=’001’ et ccoaff=’H’
DROP TABLE IF EXISTS temp_local_pev_parcelle;

CREATE TABLE temp_local_pev_parcelle AS (
  SELECT
    local10.idpar,
    count(*) AS nlocal,

    count(CASE WHEN local10.dteloc = '1' THEN '1' END)
      AS nlocmaison,
    count(CASE WHEN local10.dteloc = '2' THEN '1' END)
      AS nlocappt,
    count(CASE WHEN local10.dteloc = '3' THEN '1' END)
      AS nlocdep,
    count(CASE WHEN local10.dteloc = '4' THEN '1' END)
      AS nloccom,
    count(CASE WHEN
      local10.dteloc = '1' OR local10.dteloc = '2'
      THEN '1' END) AS nloclog,

    count(CASE WHEN
      local10.dteloc = '4' AND local10.cconlc IN ('U', 'US', 'UN', 'UE', 'UG')
      THEN '1' END) AS nloccomsec,

    count(CASE WHEN
        local10.dteloc = '4' AND local10.cconlc IN (
          'CA', 'CD', 'CM', 'CH', 'ME', 'CB', 'AT', 'AU', 'DC', 'SM'
        )
      THEN '1' END) AS nloccomter,

    count(CASE WHEN (
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H')
      THEN '1' END) AS nlogh,

    count(CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND pev.ccthp = 'V'
      THEN '1' END) AS nloghvac,

    count(CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND pev.ccthp = 'B'
      THEN '1' END) AS nloghmeu,

    count(CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND pev.ccthp = 'L'
      THEN '1' END) AS nloghloue,

    count(CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND pev.ccthp = 'P'
      THEN '1' END) AS nloghpp,

    count(CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND (pev.ccthp = 'G' OR pev.ccthp = 'X')
      THEN '1' END) AS nloghautre,

    count(CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND (pev.ccthp = 'N' OR pev.ccthp = 'T' OR pev.ccthp = 'D' OR pev.ccthp = 'R')
      THEN '1' END) AS nloghnonh,

    count(CASE WHEN
        local10.hlmsem = '5'
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
      THEN '1' END) AS nloghlm

  FROM local10
  LEFT JOIN pev
    ON local10.idlocal = pev.idlocal
  GROUP BY local10.idpar
);

CREATE INDEX temp_local_pev_parcelle_idpar_idx
ON temp_local_pev_parcelle
USING btree(idpar);


UPDATE parcellaire SET
  nlocal = t.nlocal,
  nlocmaison = t.nlocmaison,
  nlocappt = t.nlocappt,
  nloclog = t.nloclog,
  nloccom = t.nloccom,
  nloccomsec = t.nloccomsec,
  nloccomter = t.nloccomter,
  nlocdep = t.nlocdep,
  nlogh = t.nlogh,
  nloghvac = t.nloghvac,
  nloghmeu = t.nloghmeu,
  nloghloue = t.nloghloue,
  nloghpp = t.nloghpp,
  nloghautre = t.nloghautre,
  nloghnonh = t.nloghnonh,
  nloghlm = t.nloghlm
FROM temp_local_pev_parcelle AS t
WHERE t.idpar = parcellaire.idpar;

DROP TABLE temp_local_pev_parcelle;

CREATE VIEW ncp_data AS (
  WITH compte_proprietaire AS (
    -- compte proprietaire de la parcelle
    SELECT
        parcellaire.idpar,
        null::text AS idlocal,
        parcellaire.idprocpte
      FROM parcellaire

    UNION ALL

    -- comptes proprietaires des locaux
    SELECT
        parcellaire.idpar,
        local10.idlocal,
        local10.idprocpte
      FROM parcellaire
      LEFT OUTER JOIN local10
        ON parcellaire.idpar = local10.idpar
  )

  SELECT
      idpar,
      count(DISTINCT idprocpte) AS ncp
    FROM compte_proprietaire
    GROUP BY idpar
);

UPDATE parcellaire SET ncp = ncp_data.ncp
  FROM ncp_data
  WHERE ncp_data.idpar = parcellaire.idpar;

DROP TABLE IF EXISTS temp_local_pevprincipale_parcelle;

CREATE TABLE temp_local_pevprincipale_parcelle AS (
  SELECT
    idpar,
    sum(dsupdc)::numeric AS stoth,
    sum(coalesce(dep1_dsueic, 0)
      + coalesce(dep2_dsueic, 0)
      + coalesce(dep3_dsueic, 0)
      + coalesce(dep4_dsueic, 0)
    )::numeric AS stotdsueic

  FROM (local10 LEFT JOIN pev ON local10.idlocal = pev.idlocal)
  LEFT JOIN pevprincipale
    ON pev.pev = pevprincipale.pev
  GROUP BY idpar
);

CREATE INDEX temp_local_pevprincipale_parcelle_idpar_idx
ON temp_local_pevprincipale_parcelle
USING btree(idpar);

UPDATE parcellaire SET
  stoth = t.stoth,
  stotdsueic = t.stotdsueic
FROM temp_local_pevprincipale_parcelle AS t
WHERE t.idpar = parcellaire.idpar;

DROP TABLE temp_local_pevprincipale_parcelle;

DROP TABLE IF EXISTS temp_local_pevprofessionnelle_parcelle;

CREATE TABLE temp_local_pevprofessionnelle_parcelle AS (
  SELECT
    idpar,
    sum(vsurzt)::numeric AS stotp

  FROM (local10 LEFT JOIN pev ON local10.idlocal = pev.idlocal)
  LEFT JOIN pevprofessionnelle ON pev.pev = pevprofessionnelle.pev
  GROUP BY idpar
);

CREATE INDEX temp_local_pevprofessionnelle_parcelle_idpar_idx
ON temp_local_pevprofessionnelle_parcelle
USING btree(idpar);

UPDATE parcellaire SET
  stotp = t.stotp
FROM temp_local_pevprofessionnelle_parcelle AS t
WHERE t.idpar = parcellaire.idpar;

DROP TABLE temp_local_pevprofessionnelle_parcelle;


DROP TABLE IF EXISTS temp_local00_parcelle;

CREATE TABLE temp_local00_parcelle AS (
  SELECT
    idpar,
    count(DISTINCT idbat) AS nbat
  FROM local00
  GROUP BY idpar
);

CREATE INDEX temp_local00_parcelle_idpar_idx
ON temp_local00_parcelle
USING btree(idpar);

UPDATE parcellaire SET
  nbat = t.nbat
FROM temp_local00_parcelle AS t
WHERE parcellaire.idpar = t.idpar;

DROP TABLE temp_local00_parcelle;

UPDATE parcellaire SET
  spevtot = coalesce(stoth, 0) + coalesce(stotdsueic, 0)
  + coalesce(stotp, 0) + coalesce(stotd, 0);


WITH jannat AS (
  SELECT
    parcellaire.idpar,
    CASE
      WHEN count(local10.idlocal) = 0 THEN -1                                               -- pas de local
      WHEN count(local10.jannat) FILTER (WHERE local10.jannat != '0000') = 0 THEN 0 -- pas de date trouvée
      ELSE min(local10.jannat::integer) FILTER (WHERE local10.jannat != '0000')
    END AS jannatmin,

    CASE
      WHEN count(local10.idlocal) = 0 THEN -1                                               -- pas de local
      WHEN count(local10.jannat) FILTER (WHERE local10.jannat != '0000') = 0 THEN 0 -- pas de date trouvée
      ELSE max(local10.jannat::integer) FILTER (WHERE local10.jannat != '0000')
    END AS jannatmax,

    CASE
      WHEN
        count(local10.idlocal)
          FILTER (WHERE local10.dteloc = '1' OR local10.dteloc = '2')
          = 0
        THEN -1  -- pas de local d'habitation
      WHEN
        count(local10.jannat)
          FILTER (WHERE local10.jannat != '0000' AND (local10.dteloc = '1' OR local10.dteloc = '2'))
          = 0
        THEN 0   -- pas de date trouvée pour les locaux d'habitation
      ELSE
        min(local10.jannat::integer)
          FILTER (WHERE local10.jannat != '0000' AND (local10.dteloc = '1' OR local10.dteloc = '2'))
    END
    AS jannatminh,

    CASE
      WHEN
        count(local10.idlocal)
          FILTER (WHERE local10.dteloc = '1' OR local10.dteloc = '2')
          = 0
        THEN -1  -- pas de local d'habitation
      WHEN
        count(local10.jannat)
          FILTER (WHERE local10.jannat != '0000' AND (local10.dteloc = '1' OR local10.dteloc = '2'))
          = 0
        THEN 0   -- pas de date trouvée pour les locaux d'habitation
      ELSE
        max(local10.jannat::integer)
          FILTER (WHERE local10.jannat != '0000' AND (local10.dteloc = '1' OR local10.dteloc = '2'))
    END
    AS jannatmaxh

  FROM parcellaire
  LEFT OUTER JOIN local10
    ON local10.idpar = parcellaire.idpar
  GROUP BY parcellaire.idpar
)
UPDATE parcellaire SET
  jannatmin = jannat.jannatmin,
  jannatmax = jannat.jannatmax,
  jannatminh = jannat.jannatminh,
  jannatmaxh = jannat.jannatmaxh
FROM jannat
WHERE jannat.idpar = parcellaire.idpar;

WITH countlots AS (
  SELECT
    parcellaire.idpar,
    count(lots.idlot) AS nlot
  FROM parcellaire
  LEFT OUTER JOIN lots
    ON parcellaire.idpar = lots.idpar
  GROUP BY parcellaire.idpar
)
UPDATE parcellaire SET
  nlot = countlots.nlot
FROM countlots
WHERE countlots.idpar = parcellaire.idpar;

WITH dry AS (
  SELECT
    idpar,
    CASE substr(jdatat, 5, 4)
      WHEN '' THEN 0
      ELSE substr(jdatat, 5, 4)::int
    END
    AS jdatat_year
  FROM parcellaire
)
UPDATE parcellaire SET
  jdatatan =
    CASE
      WHEN dry.jdatat_year > 0 AND dry.jdatat_year <= 10
        THEN 2000 + dry.jdatat_year
      WHEN dry.jdatat_year > 10 AND dry.jdatat_year <= 20
        THEN 0
      WHEN dry.jdatat_year > 20 AND dry.jdatat_year <= 99
        THEN 1900 + dry.jdatat_year
      WHEN dry.jdatat_year >= 100 AND dry.jdatat_year <= 119
        THEN 0
      WHEN dry.jdatat_year >= 120 AND dry.jdatat_year <= 200
        THEN 10 * dry.jdatat_year
      WHEN dry.jdatat_year >= 201 AND dry.jdatat_year <= 299
        THEN 0
      WHEN dry.jdatat_year >= 300 AND dry.jdatat_year <= 999
        THEN 1000 + dry.jdatat_year
      WHEN dry.jdatat_year >= 1000 AND dry.jdatat_year < 1120
        THEN 0
      WHEN dry.jdatat_year >= 1120 AND dry.jdatat_year <= 1199
        THEN 800 + dry.jdatat_year
      ELSE dry.jdatat_year
    END
FROM dry
WHERE dry.idpar = parcellaire.idpar;

WITH parcellaire_with_cgrnum AS (
  SELECT
    parcellaire.idpar,
    SUM(suf.dcntsf::int)
      FILTER (WHERE suf.cgrnum IN ('01', '02', '03', '04', '05', '06', '07', '08'))
      AS dcntnaf,
    SUM(suf.dcntsf::int)
      FILTER (WHERE suf.cgrnum IN ('09', '10', '11', '12', '13'))
      AS dcntarti
  FROM parcellaire
  LEFT OUTER JOIN suf
    ON parcellaire.idpar = suf.idpar
  GROUP BY parcellaire.idpar
)
UPDATE parcellaire SET
  dcntnaf = parcellaire_with_cgrnum.dcntnaf,
  dcntarti = parcellaire_with_cgrnum.dcntarti
FROM parcellaire_with_cgrnum
WHERE parcellaire_with_cgrnum.idpar = parcellaire.idpar;


