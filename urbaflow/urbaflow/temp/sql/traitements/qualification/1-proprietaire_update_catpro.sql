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
      WHEN codgrmtxt = 'COPROPRIETES' THEN 'COPROPRIETE'
      WHEN codgrmtxt = 'ETABLISSEMENTS PUBLICS OU ORGANISMES ASSIMILES' THEN 'AUTRE_PUB'
      WHEN codgrmtxt = 'PERSONNES MORALES PRIVEES' THEN 'PERSONNES MORALES PRIVEES'
      WHEN codgrmtxt = 'PERSONNES PHYSIQUES' THEN 'PERSONNES PHYSIQUES'
      ELSE 'AUTRE'
      END;

UPDATE proprietaire
  SET catpro = 'EPCI'
  WHERE ddenom ilike 'COMMUNAUTE DE COMMUNES%'
    ;     

UPDATE proprietaire
  SET catpro = c.catpro
  FROM correction_typologie_proprietaire AS c
  WHERE c.ddenom = proprietaire.ddenom;


