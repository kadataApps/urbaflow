UPDATE
    suf
SET
    idsuf = ccodep || ccocom || CASE
        WHEN trim(ccopre) = ''
            THEN
                '000'
        ELSE
            ccopre
    END || coalesce(trim(ccosec), '') || dnupla || ccosub,
    idpar = ccodep || ccocom || CASE
        WHEN trim(ccopre) = ''
            THEN
                '000'
        ELSE
            ccopre
    END || coalesce(trim(ccosec), '') || dnupla
