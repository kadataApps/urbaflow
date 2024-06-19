

WITH gdprop_agg AS (
  SELECT p.dnuper,
  SUM(CASE WHEN logh ='t' THEN 1 END) nlogh, 
  SUM(CASE WHEN loghvac = 't' THEN 1 END) nloghvac,
  SUM(CASE WHEN loghpp = 't' THEN 1 END) nloghpp,
  SUM(CASE WHEN loghmeu = 't' THEN 1 END) nloghmeu,
  SUM(CASE WHEN logloue = 't' THEN 1 END) nlogloue,
  SUM(CASE WHEN loghautre = 't' THEN 1 END) nloghautre,
  SUM(CASE WHEN loghnonh = 't' THEN 1 END) nloghnonh,
  SUM(CASE WHEN loghlm = 't' THEN 1 END) nloghlm
  FROM proprietaire  p, local10 l
  WHERE p.idprocpte = l.idprocpte
  GROUP BY p.dnuper
) UPDATE proprietaire
    SET nlogh = gdprop_agg.nlogh,
    nloghvac = gdprop_agg.nloghvac,
    nloghpp = gdprop_agg.nloghpp,
    nloghmeu = gdprop_agg.nloghmeu,
    nlogloue = gdprop_agg.nlogloue,
    nloghautre = gdprop_agg.nloghautre,
    nloghnonh = gdprop_agg.nloghnonh,
    nloghlm = gdprop_agg.nloghlm
    FROM gdprop_agg
    WHERE proprietaire.dnuper = gdprop_agg.dnuper;

UPDATE proprietaire
  SET gdprop = CASE
    WHEN nlogh  >= 10 THEN 't'
    ELSE 'f'
  END;