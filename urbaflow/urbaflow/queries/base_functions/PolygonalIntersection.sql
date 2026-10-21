SET SEARCH_PATH TO public;

CREATE OR REPLACE FUNCTION PolygonalIntersection(a geometry, b geometry)
RETURNS geometry AS $$
  SELECT 
    ST_Collect(geom)
  FROM 
    (SELECT (ST_Dump(ST_Intersection(a, b))).geom 
    ) SQ
  WHERE 
    ST_GeometryType(geom) = 'ST_Polygon' 
    OR ST_GeometryType(geom) = 'ST_MultiPolygon';
$$ LANGUAGE SQL;