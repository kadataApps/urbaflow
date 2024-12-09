
UPDATE parcellaire SET catpro_niv2 =
	CASE 
		WHEN catpro = 'COPROPRIETE'
			THEN 'Copropriétés/ASL'
		WHEN typproppro = 'PERSONNES PHYSIQUES' AND ndroitindi = 2
			THEN 'Indivisions simples (2 indivisaires)'
		WHEN typproppro = 'PERSONNES PHYSIQUES' AND ndroitindi > 2
			THEN 'Indivisions complexes (3+ indivisaires)'
		WHEN descprop = 'PLEINE PROPRIETE' AND typproppro = 'PERSONNES PHYSIQUES' 
			THEN 'Monopropriétés'
		WHEN typproppro = 'PERSONNES MORALES PRIVEES' AND ndroitpro = 1
			THEN 'Sociétés'
		WHEN typproppro = 'PERSONNES MORALES PRIVEES' AND ndroitpro > 1
			THEN 'Groupements de sociétés'
		WHEN typproppro = 'ETAT' OR typproppro = 'REGION' OR typproppro = 'DEPARTEMENT' OR typproppro = 'COMMUNE' 
			OR catpro = 'EPCI' 
			THEN 'Public'
		WHEN typproppro = 'OFFICE HLM' OR typproppro = 'ETABLISSEMENTS PUBLICS OU ORGANISMES ASSIMILES' OR catpro = 'AUTRE_PUB' 
			OR catpro = 'AMENAGEUR_PUB' OR catpro = 'EPF'
			THEN 'Parapublic'
		ELSE 'Autres'
	END;
