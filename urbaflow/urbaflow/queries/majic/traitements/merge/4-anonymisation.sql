UPDATE parcellaire SET
  ddenomprop = 'Pers. Physique. (Id.: ' || idprocpte || ')',
  ddenomproppro = 'Pers. Physique. (Id.: ' || idprocpte || ')'
WHERE typproppro = 'PERSONNES PHYSIQUES';

UPDATE parcellaire SET
  ddenompropges = 'Pers. Physique. (Id.: ' || idprocpte || ')'
WHERE typpropges = 'PERSONNES PHYSIQUES';
