INSERT INTO commune_france (
    commune, geo_commune, ccodep, ccocom, libcom, typcom, ruract, carvoi,
    annul, dteannul, dtecreart, typvoi, motclas, idcom
)
SELECT DISTINCT ON (code_dep, code_commune)
    code_dep || code_commune,
    code_dep || code_commune,
    code_dep,
    code_commune,
    libelle,
    NULLIF(type_commune_actuel, ''),
    NULLIF(rur_actuel, ''),
    NULLIF(caractere_voie, ''),
    NULLIF(annulation, ''),
    NULLIF(date_annulation, '00000000'),
    NULLIF(date_creation_article, '00000000'),
    NULLIF(type_voie, ''),
    NULLIF(mot_classant, ''),
    code_dep || code_commune
FROM dgfip_topo
WHERE NULLIF(code_dep, '') IS NOT NULL
  AND NULLIF(code_commune, '') IS NOT NULL
  AND NULLIF(code_voie, '') IS NULL;

INSERT INTO voie_france (
    voie, ccodep, ccocom, ccoriv, natvoi, libvoi, typcom, ruract, carvoi,
    annul, dteannul, dtecreart, typvoi, motclas, commune, idvoie
)
SELECT
    code_dep || code_commune || code_voie,
    code_dep,
    code_commune,
    code_voie,
    NULLIF(nature_voie, ''),
    NULLIF(libelle, ''),
    NULLIF(type_commune_actuel, ''),
    NULLIF(rur_actuel, ''),
    NULLIF(caractere_voie, ''),
    NULLIF(annulation, ''),
    NULLIF(date_annulation, '00000000'),
    NULLIF(date_creation_article, '00000000'),
    NULLIF(type_voie, ''),
    NULLIF(mot_classant, ''),
    code_dep || code_commune,
    code_dep || code_commune || code_voie
FROM dgfip_topo
WHERE NULLIF(code_dep, '') IS NOT NULL
  AND NULLIF(code_commune, '') IS NOT NULL
  AND NULLIF(code_voie, '') IS NOT NULL;