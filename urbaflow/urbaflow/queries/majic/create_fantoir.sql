DROP TABLE IF EXISTS commune_france;
CREATE TABLE commune_france (
    commune text,
    annee text,
    ccodep text,
    ccodir text,
    ccocom text,
    clerivili text,
    libcom text,
    typcom text,
    ruract text,
    carvoi text,
    indpop text,
    poprel integer,
    poppart integer,
    popfict integer,
    annul text,
    dteannul text,
    dtecreart text,
    codvoi text,
    typvoi text,
    indldnbat text,
    motclas text,
    geo_commune text,
    lot text,
    idcom text
);


DROP TABLE IF EXISTS voie_france;
CREATE TABLE voie_france (
    voie text,
    annee text,
    ccodep text,
    ccodir text,
    ccocom text,
    commune text,
    natvoiriv text,
    ccoriv text,
    clerivili text,
    natvoi text,
    libvoi text,
    typcom text,
    ruract text,
    carvoi text,
    indpop text,
    poprel text,
    poppart integer,
    popfict integer,
    annul text,
    dteannul text,
    dtecreart text,
    codvoi text,
    typvoi text,
    indldnbat text,
    motclas text,
    lot text,
    idvoie text
);


COMMENT ON TABLE voie_france IS 'Voie (Fantoir)';
COMMENT ON COLUMN voie_france.ccodep IS 'Code département - Code département INSEE';
COMMENT ON COLUMN voie_france.ccodir IS 'Code direction - Code direction dge';
COMMENT ON COLUMN voie_france.ccocom IS 'Code commune - code commune définie par Majic2';
COMMENT ON COLUMN voie_france.natvoiriv IS 'Nature de voie rivoli - ';
COMMENT ON COLUMN voie_france.ccoriv IS 'Code voie Rivoli - identifiant de voie dans la commune';
COMMENT ON COLUMN voie_france.clerivili IS 'Clé RIVOLI - zone alphabétique fournie par MAJIC2';
COMMENT ON COLUMN voie_france.natvoi IS 'nature de voie - ';
COMMENT ON COLUMN voie_france.libvoi IS 'libellé de voie - ';
COMMENT ON COLUMN voie_france.typcom IS 'Type de commune actuel (R ou N) - N - commune rurale, R - commune rencencée';
COMMENT ON COLUMN voie_france.ruract IS 'RUR actuel - indique si la commune est pseudo-recensée ou non (3-commune pseudo-recensée, blanc si rien)';
COMMENT ON COLUMN voie_france.carvoi IS 'caractère de voie - zone indiquant si la voie est privée (1) ou publique (0)';
COMMENT ON COLUMN voie_france.indpop IS 'indicateur de population - Précise la dernière situation connue de la commune au regard de la limite de 3000 habitants (= blanc si < 3000 h sinon = *).';
COMMENT ON COLUMN voie_france.poprel IS 'population réelle - dénombre la population recencée lors du dernier recensement';
COMMENT ON COLUMN voie_france.poppart IS 'population à part - dénombre la population comptée à part dans la commune';
COMMENT ON COLUMN voie_france.popfict IS 'population fictive - population fictive de la commune';
COMMENT ON COLUMN voie_france.annul IS 'Annulation Cet article indique que plus aucune entité topo n’est représentée par ce code. - O - voie annulée sans transfert, Q - voie annulée avec transfert, Q - commune annulée avec transfert.';
COMMENT ON COLUMN voie_france.dteannul IS 'date d''annulation - ';
COMMENT ON COLUMN voie_france.dtecreart IS 'Date de création de l''article - Date à laquelle l''article a été créé par création MAJIC2.';
COMMENT ON COLUMN voie_france.codvoi IS 'Code identifiant la voie dans MAJIC2. - Permet de faire le lien entre le code voie RIVOLI et le code voie MAJIC2.';
COMMENT ON COLUMN voie_france.typvoi IS 'Type de voie - Indicateur de la classe de la voie. - 1 - voie, 2 - ensemble immobilier, 3 - lieu-dit, 4 -  pseudo-voie, 5 - voie provisoire.';
COMMENT ON COLUMN voie_france.indldnbat IS 'Indicateur lieu-dit non bâti - Zone servie uniquement pour les lieux-dits.Permet d’indiquer si le lieu-dit comporte ou non un bâtiment dans MAJIC.1 pour lieu-dit non bâti, 0 sinon.';
COMMENT ON COLUMN voie_france.motclas IS 'Mot classant - Dernier mot entièrement alphabétique du libellé de voie - Permet de restituer l''ordre alphabétique.';
COMMENT ON COLUMN voie_france.idvoie IS 'id pour croisement avec parcelles';

COMMENT ON TABLE commune_france IS 'Commune (Fantoir)';
COMMENT ON COLUMN commune_france.ccodep IS 'Code département - Code département INSEE';
COMMENT ON COLUMN commune_france.ccodir IS 'Code direction - Code direction dge';
COMMENT ON COLUMN commune_france.ccocom IS 'Code commune - code commune définie par Majic2';
COMMENT ON COLUMN commune_france.clerivili IS 'Clé RIVOLI - zone alphabétique fournie par MAJIC2';
COMMENT ON COLUMN commune_france.libcom IS 'Libellé - désignation de la commune';
COMMENT ON COLUMN commune_france.typcom IS 'Type de commune actuel (R ou N) - N - commune rurale, R - commune rencencée';
COMMENT ON COLUMN commune_france.ruract IS 'RUR actuel - indique si la commune est pseudo-recensée ou non (3-commune pseudo-recensée, blanc si rien)';
COMMENT ON COLUMN commune_france.carvoi IS 'caractère de voie - zone indiquant si la voie est privée (1) ou publique (0)';
COMMENT ON COLUMN commune_france.indpop IS 'indicateur de population - Précise la dernière situation connue de la commune au regard de la limite de 3000 habitants (= blanc si < 3000 h sinon = *).';
COMMENT ON COLUMN commune_france.poprel IS 'population réelle - dénombre la population recencée lors du dernier recensement';
COMMENT ON COLUMN commune_france.poppart IS 'population à part - dénombre la population comptée à part dans la commune';
COMMENT ON COLUMN commune_france.popfict IS 'population fictive - population fictive de la commune';
COMMENT ON COLUMN commune_france.annul IS 'Annulation Cet article indique que plus aucune entité topo n’est représentée par ce code. - O - voie annulée sans transfert, Q - voie annulée avec transfert, Q - commune annulée avec transfert.';
COMMENT ON COLUMN commune_france.dteannul IS 'date d''annulation - ';
COMMENT ON COLUMN commune_france.dtecreart IS 'Date de création de l''article - Date à laquelle l''article a été créé par création MAJIC2.';
COMMENT ON COLUMN commune_france.codvoi IS 'Code identifiant la voie dans MAJIC2. - Permet de faire le lien entre le code voie RIVOLI et le code voie MAJIC2.';
COMMENT ON COLUMN commune_france.typvoi IS 'Type de voie - Indicateur de la classe de la voie. - 1 - voie, 2 - ensemble immobilier, 3 - lieu-dit, 4 -  pseudo-voie, 5 - voie provisoire.';
COMMENT ON COLUMN commune_france.indldnbat IS 'Indicateur lieu-dit non bâti - Zone servie uniquement pour les lieux-dits.Permet d’indiquer si le lieu-dit comporte ou non un bâtiment dans MAJIC.1 pour lieu-dit non bâti, 0 sinon.';
COMMENT ON COLUMN commune_france.motclas IS 'Mot classant - Dernier mot entièrement alphabétique du libellé de voie - Permet de restituer l''ordre alphabétique.';
COMMENT ON COLUMN commune_france.idcom IS 'id pour croisement avec parcelles';