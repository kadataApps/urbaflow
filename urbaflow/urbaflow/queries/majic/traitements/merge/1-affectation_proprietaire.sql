-- 4 - affectation propriétaire

CREATE TABLE temp_prop_parcelle AS (

    WITH proprietaire_aux AS (
        SELECT DISTINCT
            idprocpte,
            codgrmtxt,
            codgrm,
            ccodro,
            ccodem,
            ddenom,
            typedroit,
            catpro,
            gdprop
        FROM proprietaire
        ORDER BY idprocpte, codgrm, ccodro, ccodem
    )

    SELECT
        idprocpte,
        string_agg(DISTINCT codgrmtxt, ', ') AS typprop,
        string_agg(DISTINCT ddenom, ', ') AS ddenomprop,

        count(*) AS ndroit,
        count(CASE ccodem WHEN 'I' THEN 1 END) AS ndroitindi,
        string_agg(DISTINCT typedroit, ', ') AS typedroit,

        --   droit propriétaire
        count(CASE typedroit WHEN 'P' THEN 1 END) AS ndroitpro,
        string_agg(
            DISTINCT CASE typedroit WHEN 'P' THEN codgrmtxt END, ', '
        ) AS typproppro,
        string_agg(
            DISTINCT CASE typedroit WHEN 'P' THEN ddenom END, ', '
        ) AS ddenomproppro,
        string_agg(
            DISTINCT CASE typedroit WHEN 'P' THEN catpro END, ', '
        ) AS catproppro,

        --   droits gestionnaire
        count(CASE typedroit WHEN 'G' THEN 1 END) AS ndroitges,
        string_agg(
            DISTINCT CASE typedroit WHEN 'G' THEN codgrmtxt END, ', '
        ) AS typpropges,
        string_agg(
            DISTINCT CASE typedroit WHEN 'G' THEN ddenom END, ', '
        ) AS ddenompropges,
        string_agg(
            DISTINCT CASE typedroit WHEN 'G' THEN catpro END, ', '
        ) AS catpropges,
        CASE
            WHEN count(CASE WHEN gdprop = 't' THEN 1 END) > 0 THEN 't'
        END AS presgdprop,

        (
            CASE
                WHEN count(CASE WHEN codgrm = '7' THEN TRUE END) > 0
                    THEN 'COPROPRIETE'
                WHEN count(CASE WHEN ccodem = 'I' THEN TRUE END) <= 2
                    THEN 'INDIVISION SIMPLE'
                WHEN count(CASE WHEN ccodem = 'I' THEN TRUE END) > 2
                    THEN 'INDIVISION'
                WHEN count(CASE WHEN ccodem = 'L' THEN TRUE END) > 0
                    THEN 'LITIGE'
                WHEN
                    count(
                        CASE
                            WHEN
                                ccodro = 'B' OR ccodro = 'E' OR ccodro = 'V'
                                THEN TRUE
                        END
                    )
                    > 0
                    THEN 'BAIL EMPHYTEOTIQUE'
                WHEN count(CASE WHEN ccodro = 'U' THEN TRUE END) > 0
                    THEN 'SEP. NUE-PROPRIETE / USUFRUIT'
                WHEN string_agg(DISTINCT ccodro, ', ') = 'P'
                    THEN 'PLEINE PROPRIETE'
                ELSE 'AUTRE'
            END
        ) AS descprop

    FROM proprietaire_aux
    GROUP BY idprocpte
);

CREATE INDEX temp_prop_parcelle_idprocpte_idx
ON temp_prop_parcelle
USING btree (idprocpte);

UPDATE parcellaire SET
    ndroit = temp_prop_parcelle.ndroit,
    ndroitindi = temp_prop_parcelle.ndroitindi,
    typedroit = temp_prop_parcelle.typedroit,
    ndroitpro = temp_prop_parcelle.ndroitpro,
    ndroitges = temp_prop_parcelle.ndroitges,
    typprop = temp_prop_parcelle.typprop,
    typproppro = temp_prop_parcelle.typproppro,
    typpropges = temp_prop_parcelle.typpropges,
    ddenomprop = temp_prop_parcelle.ddenomprop,
    ddenompropges = temp_prop_parcelle.ddenompropges,
    catpropges = temp_prop_parcelle.catpropges,
    ddenomproppro = temp_prop_parcelle.ddenomproppro,
    catproppro = temp_prop_parcelle.catproppro,
    presgdprop = temp_prop_parcelle.presgdprop,
    descprop = temp_prop_parcelle.descprop
FROM temp_prop_parcelle
WHERE temp_prop_parcelle.idprocpte = parcellaire.idprocpte;

DROP TABLE temp_prop_parcelle;



CREATE VIEW ndroitpro_data AS (
    WITH parcelle_bati_dnuper AS (
    -- dnuper avec droit de type proprietaire sur la parcelle
        SELECT
            parcellaire.idpar,
            proprietaire.dnuper
        FROM parcellaire LEFT OUTER JOIN proprietaire
            ON parcellaire.idprocpte = proprietaire.idprocpte
        WHERE proprietaire.typedroit = 'P'

        UNION ALL

        -- comptes proprietaires des locaux
        SELECT
            parcellaire.idpar,
            proprietaire.dnuper
        FROM parcellaire
        LEFT OUTER JOIN local10
            ON parcellaire.idpar = local10.idpar
        LEFT OUTER JOIN proprietaire
            ON local10.idprocpte = proprietaire.idprocpte
        WHERE proprietaire.typedroit = 'P'
    )

    SELECT
        idpar,
        count(DISTINCT dnuper) AS ndroitpro_parcelle_bati
    FROM parcelle_bati_dnuper
    GROUP BY idpar
);

UPDATE parcellaire SET
    ndroitpro_parcelle_bati = ndroitpro_data.ndroitpro_parcelle_bati
FROM ndroitpro_data
WHERE ndroitpro_data.idpar = parcellaire.idpar;


-- typedroit
-- B, R   Bailleur, Preneur
-- B, G, R  Bailleur, gestionnaire, Preneur
-- E, P Emphytéote, propriétaire
-- E, G, P Emphytéote, gestionnaire, propriétaire
-- V, W  Bailleur, Preneur (réhab)


-- G, P, S gestionnaire, propriétaire, Syndic de copropriété
-- P, S propriétaire, Syndic de copropriété

-- A, P Propriétaire, Locataire Attributaire

-- N, U Nu-Propriétiare, Usufruitier
-- G, N, U
-- N, P, U


-- G, P : gestionnaire, propriétaire
-- P
