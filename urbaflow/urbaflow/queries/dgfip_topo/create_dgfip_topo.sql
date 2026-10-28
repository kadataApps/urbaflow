DO $$
BEGIN
    EXECUTE format('DROP TABLE IF EXISTS %I.commune_france', current_schema());
    EXECUTE format('DROP TABLE IF EXISTS %I.voie_france', current_schema());
END
$$;
CREATE TABLE commune_france (
    commune text,
    geo_commune text,
    ccodep text,
    ccocom text,
    libcom text,
    typcom text,
    ruract text,
    carvoi text,
    annul text,
    dteannul text,
    dtecreart text,
    typvoi text,
    motclas text,
    idcom text
);

CREATE TABLE voie_france (
    voie text,
    ccodep text,
    ccocom text,
    ccoriv text,
    natvoi text,
    libvoi text,
    typcom text,
    ruract text,
    carvoi text,
    annul text,
    dteannul text,
    dtecreart text,
    typvoi text,
    motclas text,
    commune text,
    idvoie text
);