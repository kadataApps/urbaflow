UPDATE parcellaire SET
  dlibvoi = trim(coalesce(v.natvoi, '') || ' ' || coalesce(v.libvoi, ''))
FROM [IMPORT_SCHEMA].voie_france AS v
WHERE v.idvoie = parcellaire.idvoie;


UPDATE parcellaire SET
  adressepar = trim(
    coalesce(nullif(regexp_replace(dnvoiri, '[^0-9]*', '0')::integer, 0)::text, '')
    || coalesce(' ' || dindic, '')
    || coalesce(' ' || dlibvoi, '')
  );

UPDATE parcellaire SET
  libcom = c.libcom
FROM [IMPORT_SCHEMA].commune_france AS c
WHERE parcellaire.idcom = c.idcom;
