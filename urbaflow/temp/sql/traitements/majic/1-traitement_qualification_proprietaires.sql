-- Traitement proprietaires
ALTER TABLE proprietaire
ADD COLUMN idprodroit text,
ADD COLUMN idprocpte text,
ADD COLUMN idpersonne text,
ADD COLUMN idvoie text,
ADD COLUMN idcom text,
ADD COLUMN idcomtxt text,
ADD COLUMN ccodrotxt char(88),
ADD COLUMN typedroit char(1),
ADD COLUMN dnatprtxt text,
ADD COLUMN ccogrmtxt text,
ADD COLUMN codgrm text,
ADD COLUMN codgrmtxt text,
ADD COLUMN locprop text,
ADD COLUMN locproptxt text,
ADD COLUMN codnom text;

UPDATE proprietaire SET
        idprodroit = ccodep || ccocom || dnupro || dnulp,
        idprocpte = ccodep || ccocom || dnupro,
        idpersonne  = ccodep || dnuper,
        idvoie  = ccodep || ccocom || ccoriv,
        idcom  = ccodep || ccocom,
        idcomtxt = ccodep || ccocom, -- FIXME
        -- https://doc-datafoncier.cerema.fr/doc/ff/pnb10_parcelle/ndroitpro
        typedroit = CASE
          WHEN ccodro = 'B' OR ccodro = 'C' OR ccodro = 'F' OR ccodro = 'N'
            OR ccodro = 'P' OR ccodro = 'V' OR ccodro = 'X'
            THEN 'P'
          WHEN ccodro = 'A' OR ccodro = 'D' OR ccodro = 'E' OR ccodro = 'G'
            OR ccodro = 'H' OR ccodro = 'J' OR ccodro = 'K' OR ccodro = 'L'
            OR ccodro = 'O' OR ccodro = 'Q' OR ccodro = 'R' OR ccodro = 'S'
            OR ccodro = 'T' OR ccodro = 'U' OR ccodro = 'W' OR ccodro = 'Y'
            THEN 'G'
          END;

UPDATE proprietaire SET
  ccodrotxt = l.ccodro_lib
FROM libelle_ccodro AS l
WHERE l.ccodro = proprietaire.ccodro;

UPDATE proprietaire SET
  dnatprtxt = l.dnatpr_lib
FROM libelle_dnatpr AS l
WHERE l.dnatpr = proprietaire.dnatpr;

UPDATE proprietaire SET
  ccogrmtxt = l.ccogrm_lib
FROM libelle_ccogrm AS l
WHERE l.ccogrm = proprietaire.ccogrm;

-- traitement simplifié par rapport à la définition du CEREMA
-- codgrm Code groupe de personne morale harmonisé (Catégories publiques (1,
-- 2, 3, 4, 5 et 9) + copropriété (7) + autres personnes morales (0))
-- codgrmtxt = ; --Code groupe de personne morale harmonisé (Catégories
-- publiques (1, 2, 3, 4, 5 et 9) + copropriété (7) + autres personnes
-- morales (0)) traitement simplifié
UPDATE proprietaire SET
  codgrmtxt = CASE
    WHEN ccogrm = '1' THEN 'ETAT'
    WHEN ccogrm = '2' THEN 'REGION'
    WHEN ccogrm = '3' THEN 'DEPARTEMENT'
    WHEN ccogrm = '4' THEN 'COMMUNE'
    WHEN ccogrm = '5' THEN 'OFFICE HLM'
    WHEN ccogrm = '7' THEN 'COPROPRIETES'
    WHEN ccogrm = '9' THEN 'ETABLISSEMENTS PUBLICS OU ORGANISMES ASSIMILES'
    WHEN ccogrm = '0'
      OR ccogrm = '6'
      OR ccogrm = '8' THEN 'PERSONNES MORALES PRIVEES'
    ELSE 'PERSONNES PHYSIQUES'
  END,
  codgrm = CASE WHEN ccogrm in ('1','2' ,'3', '4', '5', '7', '9') THEN ccogrm ELSE '0' END;


-- suppression des espaces sur le nom des propriétaires
UPDATE proprietaire SET ddenom = trim(ddenom);

CREATE INDEX proprietaire_idprocpte_idx
ON proprietaire
USING btree(idprocpte);
