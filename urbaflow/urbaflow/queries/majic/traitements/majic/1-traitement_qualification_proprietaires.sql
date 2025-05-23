-- Traitement proprietaires
ALTER TABLE proprietaire
ADD COLUMN idprodroit TEXT,
ADD COLUMN idprocpte TEXT,
ADD COLUMN idpersonne TEXT,
ADD COLUMN idvoie TEXT,
ADD COLUMN idcom TEXT,
ADD COLUMN idcomtxt TEXT,
ADD COLUMN ccodrotxt CHAR(88),
ADD COLUMN typedroit CHAR(1),
ADD COLUMN dnatprtxt TEXT,
ADD COLUMN ccogrmtxt TEXT,
ADD COLUMN codgrm TEXT,
ADD COLUMN codgrmtxt TEXT,
ADD COLUMN locprop TEXT,
ADD COLUMN locproptxt TEXT,
ADD COLUMN codnom TEXT,
ADD COLUMN catpro TEXT,
ADD COLUMN catpro_niv2 TEXT,
ADD COLUMN nlogh INTEGER,
ADD COLUMN nloghvac INTEGER,
ADD COLUMN nloghpp INTEGER,
ADD COLUMN nloghmeu INTEGER,
ADD COLUMN nloghloue INTEGER,
ADD COLUMN nloghautre INTEGER,
ADD COLUMN nloghnonh INTEGER,
ADD COLUMN nloghlm INTEGER,
ADD COLUMN gdprop CHAR(1);

UPDATE
    proprietaire
SET
    idprodroit = ccodep || ccocom || dnupro || dnulp,
    idprocpte = ccodep || ccocom || dnupro,
    idpersonne = ccodep || dnuper,
    idvoie = ccodep || ccocom || ccoriv,
    idcom = ccodep || ccocom,
    idcomtxt = ccodep || ccocom,
    -- FIXME
    -- https://doc-datafoncier.cerema.fr/doc/ff/pnb10_parcelle/ndroitpro
    typedroit = CASE
        WHEN
            ccodro = 'B'
            OR ccodro = 'C'
            OR ccodro = 'F'
            OR ccodro = 'N'
            OR ccodro = 'P'
            OR ccodro = 'V'
            OR ccodro = 'X'
            THEN
                'P'
        WHEN
            ccodro = 'A'
            OR ccodro = 'D'
            OR ccodro = 'E'
            OR ccodro = 'H'
            OR ccodro = 'J'
            OR ccodro = 'K'
            OR ccodro = 'L'
            OR ccodro = 'O'
            OR ccodro = 'R'
            OR ccodro = 'T'
            OR ccodro = 'U'
            OR ccodro = 'W'
            OR ccodro = 'Y'
            OR ccodro = 'M'
            OR ccodro = 'Z'
            THEN
                'G'
        WHEN
            -- G = GERANT,MANDATAIRE,GESTIONNAIRE
            -- donc pas réellement gestionnaire (pas de droits réels)
            ccodro = 'G'
            -- Q = GESTIONNAIRE TAXE SUR LES BUREAUX (ILE DE FRANCE) 
            -- (pas de droits réels)
            OR ccodro = 'Q'
            -- S = SYNDIC DE COPROPRIETE (pas de droits réels)
            OR ccodro = 'S'
            THEN
                'A' -- Autre propriétaire sans droits réels
        ELSE
            'E' -- Erreur
    END;

UPDATE
    proprietaire
SET
    ccodrotxt = l.ccodro_lib
FROM
    libelle_ccodro AS l
WHERE
    l.ccodro = proprietaire.ccodro;

UPDATE
    proprietaire
SET
    dnatprtxt = l.dnatpr_lib
FROM
    libelle_dnatpr AS l
WHERE
    l.dnatpr = proprietaire.dnatpr;

UPDATE
    proprietaire
SET
    ccogrmtxt = l.ccogrm_lib
FROM
    libelle_ccogrm AS l
WHERE
    l.ccogrm = proprietaire.ccogrm;

-- traitement simplifié par rapport à la définition du CEREMA
-- codgrm Code groupe de personne morale harmonisé (Catégories publiques (1,
-- 2, 3, 4, 5 et 9) + copropriété (7) + autres personnes morales (0))
-- codgrmtxt = ; --Code groupe de personne morale harmonisé (Catégories
-- publiques (1, 2, 3, 4, 5 et 9) + copropriété (7) + autres personnes
-- morales (0)) traitement simplifié
UPDATE
    proprietaire
SET
    codgrmtxt = CASE
        WHEN ccogrm = '1'
            THEN
                'ETAT'
        WHEN ccogrm = '2'
            THEN
                'REGION'
        WHEN ccogrm = '3'
            THEN
                'DEPARTEMENT'
        WHEN ccogrm = '4'
            THEN
                'COMMUNE'
        WHEN ccogrm = '5'
            THEN
                'OFFICE HLM'
        WHEN ccogrm = '7'
            THEN
                'COPROPRIETE'
        WHEN ccogrm = '9'
            THEN
                'ETABLISSEMENT PUBLIC OU ORGANISME ASSIMILE'
        WHEN
            ccogrm = '0'
            OR ccogrm = '6'
            OR ccogrm = '8'
            THEN
                'PERSONNE MORALE'
        ELSE
            'PERSONNE PHYSIQUE'
    END,
    codgrm = CASE
        WHEN ccogrm IN ('1', '2', '3', '4', '5', '7', '9')
            THEN
                ccogrm
        ELSE
            '0'
    END;

-- suppression des espaces sur le nom des propriétaires
UPDATE
    proprietaire
SET
    ddenom = trim(ddenom);

/**
  Le champ catpro est renseigné en plusieurs étapes:
  1. utilisation du champ codgrmtxt (classification MAJIC)
  2. Correction automatique sur certains motifs de noms (Communauté de communes)
  3. correction à partir de la table correction_typologie_proprietaire
*/
UPDATE proprietaire
SET
    catpro = CASE
        WHEN codgrmtxt = 'ETAT' THEN 'AUTRE_PUB'
        WHEN codgrmtxt = 'REGION' THEN 'AUTRE_PUB'
        WHEN codgrmtxt = 'DEPARTEMENT' THEN 'AUTRE_PUB'
        WHEN codgrmtxt = 'COMMUNE' THEN 'COMMUNE'
        WHEN codgrmtxt = 'OFFICE HLM' THEN 'AUTRE_PUB'
        WHEN codgrmtxt = 'COPROPRIETE' THEN codgrmtxt
        WHEN codgrmtxt = 'ETABLISSEMENT PUBLIC OU ORGANISME ASSIMILE'
            THEN 'AUTRE_PUB'
        WHEN codgrmtxt = 'PERSONNE MORALE'
            THEN codgrmtxt
        WHEN codgrmtxt = 'PERSONNE PHYSIQUE' THEN codgrmtxt
        ELSE 'AUTRE'
    END;

UPDATE proprietaire
SET catpro = 'EPCI'
WHERE ddenom ILIKE 'COMMUNAUTE DE COMMUNES%';

UPDATE proprietaire
SET catpro = c.catpro
FROM correction_typologie_proprietaire AS c
WHERE c.ddenom = proprietaire.ddenom;


CREATE INDEX proprietaire_idprocpte_idx ON proprietaire USING btree (idprocpte);
