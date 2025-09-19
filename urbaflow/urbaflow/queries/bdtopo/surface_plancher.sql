-- Ajoute les colonnes 
-- - estimation_nb_etages, 
-- - emprise 
-- - surface_plancher
-- à la table bdtopo_batiment
ALTER TABLE bdtopo_batiment
ADD COLUMN estimation_nb_etages integer,
ADD COLUMN emprise numeric,
ADD COLUMN surface_plancher numeric;

COMMENT ON COLUMN bdtopo_batiment.estimation_nb_etages
IS 'Estimation du nombre d''étages du bâtiment';
COMMENT ON COLUMN bdtopo_batiment.emprise
IS 'Emprise au sol du bâtiment (en m²)';
COMMENT ON COLUMN bdtopo_batiment.surface_plancher
IS 'Estimation de la surface de plancher du bâtiment (en m²)';

UPDATE bdtopo_batiment SET
    emprise = st_area(geom),
    estimation_nb_etages = CASE
        WHEN hauteur IS NOT NULL
            THEN greatest(1, floor(
                CASE
                    WHEN
                        nature = 'Indifférenciée'
                        AND ('Résidentiel' IN (usage1, usage2))
                        THEN hauteur / 3.0
                    WHEN nature = 'Indifférenciée' THEN hauteur / 4.5
                    WHEN
                        nature = 'Industriel, agricole ou commercial'
                        THEN hauteur / 10.0
                    ELSE 1.0
                END
            ))
        ELSE 1.0
    END;

UPDATE bdtopo_batiment
SET surface_plancher = emprise * coalesce(nb_etages, estimation_nb_etages, 1.0);
