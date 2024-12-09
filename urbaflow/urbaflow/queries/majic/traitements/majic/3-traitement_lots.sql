UPDATE lots SET
  idlot = ccodep || ccocom || CASE
      WHEN trim(ccopre) = '' THEN '000' ELSE ccopre
    END || coalesce(trim(ccosec), '') || dnupla
    || dnupdl || dnulot,
  idpar = ccodep || ccocom || CASE
    WHEN trim(ccopre) = '' THEN '000' ELSE ccopre
  END || coalesce(trim(ccosec), '') || dnupla
