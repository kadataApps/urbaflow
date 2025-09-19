-- Calcul de la surface, surface de plancher, du ces et du cos 
-- des unités foncières (table fab.uf_etude)
-- croisées avec la table fab.bdtopo_batiment
-- (jointure spatiale, une unité foncière peut être 
-- recouverte par plusieurs bâtiments)
-- la clé primaire de la table fab.uf_etude est id_uf
-- il faut recalculer la surface de plancher à l'aide de 
-- st_area(st_intersection(uf.geom, b.geom))

UPDATE uf_etude uf
SET
    surface = st_area(uf.geom),
    semprisebatie = t.emprise,
    sspestimee = t.surface_plancher,
    ces = t.emprise / nullif(st_area(uf.geom), 0),
    cos = t.surface_plancher / nullif(st_area(uf.geom), 0)
FROM (
    SELECT
        uf.id_uf,
        sum(st_area(st_intersection(uf.geom, b.geom))) AS emprise,
        sum(
            st_area(st_intersection(uf.geom, b.geom))
            * coalesce(b.nb_etages, b.estimation_nb_etages, 1.0)
        ) AS surface_plancher
    FROM
        uf_etude AS uf,
        bdtopo_batiment AS b
    WHERE st_intersects(uf.geom, b.geom)
    GROUP BY
        uf.id_uf
) AS t
WHERE uf.id_uf = t.id_uf;
