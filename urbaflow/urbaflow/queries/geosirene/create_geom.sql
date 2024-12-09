
ALTER TABLE geosirene ADD COLUMN geom geometry(Point, 2154);

UPDATE geosirene SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(longitude::numeric, latitude::numeric), 4326),2154)
  WHERE NOT (longitude IS NULL or latitude IS NULL);

CREATE INDEX sidx_geosirene_geom ON geosirene USING gist(geom);