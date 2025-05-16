UPDATE parcellaire SET
    ddenomprop = 'Pers. Physique. (Id.: ' || idprocpte || ')',
    ddenomproppro = 'Pers. Physique. (Id.: ' || idprocpte || ')'
WHERE typproppro = 'PERSONNE PHYSIQUE';

UPDATE parcellaire SET
    ddenompropges = 'Pers. Physique. (Id.: ' || idprocpte || ')'
WHERE typpropges = 'PERSONNE PHYSIQUE';
