ALTER TABLE
cadastre_parcelles
ADD
COLUMN geo_parcelle TEXT;

UPDATE
    cadastre_parcelles
SET
    geo_parcelle
    = left(commune, 2) || '0' || right(commune, 3) || prefixe || CASE
        WHEN length(section) = 2 THEN section
        ELSE '0' || section
    END || left('0000', 4 - length(numero)) || numero;
