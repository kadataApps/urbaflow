ALTER TABLE cadastre_parcelles add column geo_parcelle text;
UPDATE cadastre_parcelles set geo_parcelle =  
  left(commune,2)
  || '0'
  || right(commune, 3)
  ||prefixe
  || CASE WHEN length("section") = 2 THEN "section" ELSE '0'||"section" end
  || left('0000', 4-length(numero))||numero;

