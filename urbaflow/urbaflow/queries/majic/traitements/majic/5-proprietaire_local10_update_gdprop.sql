WITH gdprop_agg AS (
    SELECT
        p.dnuper,
        SUM(
            CASE
                WHEN l.logh = 't' THEN
                    1
            END
        ) AS nlogh,
        SUM(
            CASE
                WHEN l.loghvac = 't' THEN
                    1
            END
        ) AS nloghvac,
        SUM(
            CASE
                WHEN l.loghpp = 't' THEN
                    1
            END
        ) AS nloghpp,
        SUM(
            CASE
                WHEN l.loghmeu = 't' THEN
                    1
            END
        ) AS nloghmeu,
        SUM(
            CASE
                WHEN l.logloue = 't' THEN
                    1
            END
        ) AS nloghloue,
        SUM(
            CASE
                WHEN l.loghautre = 't' THEN
                    1
            END
        ) AS nloghautre,
        SUM(
            CASE
                WHEN l.loghnonh = 't' THEN
                    1
            END
        ) AS nloghnonh,
        SUM(
            CASE
                WHEN l.loghlm = 't' THEN
                    1
            END
        ) AS nloghlm
    FROM
        proprietaire AS p,
        local10 AS l
    WHERE
        p.idprocpte = l.idprocpte
    GROUP BY
        p.dnuper
)

UPDATE
    proprietaire
SET
    nlogh = gdprop_agg.nlogh,
    nloghvac = gdprop_agg.nloghvac,
    nloghpp = gdprop_agg.nloghpp,
    nloghmeu = gdprop_agg.nloghmeu,
    nloghloue = gdprop_agg.nloghloue,
    nloghautre = gdprop_agg.nloghautre,
    nloghnonh = gdprop_agg.nloghnonh,
    nloghlm = gdprop_agg.nloghlm
FROM
    gdprop_agg
WHERE
    proprietaire.dnuper = gdprop_agg.dnuper;

UPDATE
    proprietaire
SET
    gdprop = CASE
        WHEN nlogh >= 10
            THEN
                't'
        ELSE
            'f'
    END;



-- Mise à jour de la table local10
-- ajout d'un champ presgdprop (présence d'un grand propriétaire)
ALTER TABLE local10
ADD COLUMN IF NOT EXISTS presgdprop boolean;

COMMENT ON COLUMN local10.presgdprop
IS 'Indique la présence d''un grand propriétaire pour le logement';

WITH idprocpte_avec_gdprop AS (
    SELECT distinct idprocpte
    FROM proprietaire
    WHERE gdprop = 't'
)   

UPDATE local10 AS l
SET presgdprop = CASE
    WHEN g.idprocpte IS NOT NULL THEN TRUE
    ELSE FALSE
END
FROM idprocpte_avec_gdprop AS g
WHERE l.idprocpte = g.idprocpte;
;

