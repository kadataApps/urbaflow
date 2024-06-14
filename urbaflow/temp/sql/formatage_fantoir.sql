
-- Traitement: commune
INSERT INTO public.commune_france
(
 commune, geo_commune, annee, ccodep, ccodir, ccocom, clerivili, libcom, typcom, ruract, carvoi, indpop, poprel, poppart, popfict, annul, dteannul, dtecreart, codvoi,
 typvoi, indldnbat, motclas, lot
)
SELECT
  REPLACE(SUBSTRING(tmp,1,6),' ', '0') AS commune,
  REPLACE(SUBSTRING(tmp,1,6),' ', '0') AS geo_commune,
  '[ANNEE]' as annee,
  SUBSTRING(tmp,1,2) AS ccodep,
  SUBSTRING(tmp,3,1) AS ccodir,
  SUBSTRING(tmp,4,3) AS ccocom,
  SUBSTRING(tmp,11,1) AS clerivili,
  SUBSTRING(tmp,12,30) AS libcom,
  CASE WHEN trim(SUBSTRING(tmp,43,1))='' THEN NULL ELSE trim(SUBSTRING(tmp,43,1)) END AS typcom,
  SUBSTRING(tmp,46,1) AS ruract,
  SUBSTRING(tmp,49,1) AS carvoi,
  SUBSTRING(tmp,50,1) AS indpop,
  CASE WHEN trim(SUBSTRING(tmp,53,7))='' THEN NULL ELSE to_number(trim(SUBSTRING(tmp,53,7)),'0000000') END AS poprel,
  to_number(SUBSTRING(tmp,60,7),'9999999') AS poppart,
  to_number(SUBSTRING(tmp,67,7),'0000000') AS popfict,
  SUBSTRING(tmp,74,1) AS annul,
  SUBSTRING(tmp,75,7) AS dteannul,
  SUBSTRING(tmp,82,7) AS dtecreart,
  SUBSTRING(tmp,104,5) AS codvoi,
  SUBSTRING(tmp,109,1) AS typvoi,
  SUBSTRING(tmp,110,1) AS indldnbat,
  SUBSTRING(tmp,113,8) AS motclas,
  '[LOT]' as lot
FROM fanr WHERE trim(SUBSTRING(tmp,4,3))  != '' AND trim(SUBSTRING(tmp,7,4))='';

-- Traitement: voie
INSERT INTO public.voie_france
(
 voie, annee, ccodep, ccodir, ccocom, natvoiriv, ccoriv, clerivili, natvoi, libvoi, typcom, ruract, carvoi, indpop, poprel, poppart, popfict, annul, dteannul,
 dtecreart, codvoi, typvoi, indldnbat, motclas,
 commune, lot
)
SELECT
  REPLACE(SUBSTRING(tmp,1,6)||SUBSTRING(tmp,104,5)||SUBSTRING(tmp,7,4),' ', '0') AS voie,
  '[ANNEE]' as annee,
  SUBSTRING(tmp,1,2) AS ccodep,
  SUBSTRING(tmp,3,1) AS ccodir,
  SUBSTRING(tmp,4,3) AS ccocom,
  CASE WHEN trim(SUBSTRING(tmp,7,1))='' THEN NULL ELSE trim(SUBSTRING(tmp,7,1)) END AS natvoiriv,
  SUBSTRING(tmp,7,4) AS ccoriv,
  SUBSTRING(tmp,11,1) AS clerivili,
  TRIM(SUBSTRING(tmp,12,4)) AS natvoi,
  SUBSTRING(tmp,16,26) AS libvoi,
  CASE WHEN trim(SUBSTRING(tmp,43,1))='' THEN NULL ELSE trim(SUBSTRING(tmp,43,1)) END AS typcom,
  SUBSTRING(tmp,46,1) AS ruract,
  CASE WHEN trim(SUBSTRING(tmp,49,1))='' THEN NULL ELSE trim(SUBSTRING(tmp,49,1)) END AS carvoi,
  SUBSTRING(tmp,50,1) AS indpop,
  SUBSTRING(tmp,53,7) AS poprel,
  to_number(SUBSTRING(tmp,60,7),'0000000') AS poppart,
  to_number(SUBSTRING(tmp,67,7),'0000000') AS popfict,
  CASE WHEN trim(SUBSTRING(tmp,74,1))='' THEN NULL ELSE trim(SUBSTRING(tmp,74,1)) END AS annul,
  SUBSTRING(tmp,75,7) AS dteannul,
  SUBSTRING(tmp,82,7) AS dtecreart,
  SUBSTRING(tmp,104,5) AS codvoi,
  CASE WHEN trim(SUBSTRING(tmp,109,1))='' THEN NULL ELSE trim(SUBSTRING(tmp,109,1)) END AS typvoi,
  CASE WHEN trim(SUBSTRING(tmp,110,1))='' THEN NULL ELSE trim(SUBSTRING(tmp,110,1)) END AS indldnbat,
  SUBSTRING(tmp,113,8) AS motclas,
  REPLACE(SUBSTRING(tmp,1,6),' ', '0') AS commune,
  '[LOT]' as lot
FROM fanr WHERE trim(SUBSTRING(tmp,4,3))  != '' AND trim(SUBSTRING(tmp,7,4))  != '';




-- 5 - adresses

UPDATE commune_france SET idcom = trim(ccodep || ccocom);
UPDATE voie_france SET idvoie = trim(ccodep) || trim(ccocom) || trim(ccoriv);
