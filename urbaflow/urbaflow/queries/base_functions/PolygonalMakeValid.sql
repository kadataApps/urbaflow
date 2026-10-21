SET SEARCH_PATH TO public;

CREATE OR REPLACE FUNCTION PolygonalMakeValid(A geometry)
RETURNS geometry AS $$
  SELECT
    ST_Collect(geom)
  FROM
    (SELECT (ST_Dump(st_makevalid(A))).geom
    ) SQ
  WHERE
    ST_GeometryType(geom) = 'ST_Polygon'
    OR ST_GeometryType(geom) = 'ST_MultiPolygon';
$$ LANGUAGE SQL;