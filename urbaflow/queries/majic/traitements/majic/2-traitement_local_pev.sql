ALTER TABLE pev
ADD COLUMN idpev text,
ADD COLUMN idlocal text,
ADD COLUMN idcom text;

ALTER TABLE local10
ADD COLUMN idlocal text,
ADD COLUMN idpar text;

ALTER TABLE local00
ADD COLUMN idpar text,
ADD COLUMN idbat text;

UPDATE pev SET
  idpev = ccodep || invar || dnupev,
  idlocal = ccodep || invar,
  idcom = ccodep || ccocom;

-- UPDATE local10 SET
-- 	idlocal = ccodep || invar,
-- 	idpar = '123'||ccodep || ccocom || CASE WHEN trim(ccopre) = '' THEN '000'
-- 	ELSE ccopre END || COALESCE(trim(ccosec),'') || dnupla ;

UPDATE local10 SET
  idlocal = ccodep || invar,

  idpar = ccodep || ccocom || CASE
    WHEN trim(ccopre) = '' THEN '000' ELSE ccopre
  END || coalesce(trim(ccosec), '') || dnupla,

  idprocpte = ccodep || ccocom || dnupro;

UPDATE local10 SET
  idbat = idpar || dnubat;

UPDATE local00 SET
  idpar = ccodep || ccocom || CASE
    WHEN trim(ccopre) = '' THEN '000' ELSE ccopre
  END || coalesce(trim(ccosec), '') || dnupla,

  idbat = ccodep || ccocom || CASE
    WHEN trim(ccopre) = '' THEN '000' ELSE ccopre
  END || coalesce(trim(ccosec), '') || dnupla || dnubat;


UPDATE local10 SET
  logh = CASE WHEN (
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H')
      THEN 't' END,
  loghvac = CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND pev.ccthp = 'V'
      THEN 't' END,
  loghpp = CASE WHEN
        (local10.dteloc = '1' OR local10.dteloc = '2')
        AND pev.dnupev = '001'
        AND pev.ccoaff = 'H'
        AND pev.ccthp = 'P'
      THEN 't' END
FROM pev
    WHERE local10.idlocal = pev.idlocal;