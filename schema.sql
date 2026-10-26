-- Estrutura do banco espacial do mapa colaborativo.
--
-- Uso (somente em banco novo):
--   spatialite data/mapa.sqlite < schema.sql
--
-- Para recriar do zero:
--   rm -f data/mapa.sqlite data/mapa.sqlite-wal data/mapa.sqlite-shm
--   spatialite data/mapa.sqlite < schema.sql

-- WAL permite ler o banco com a API rodando, sem bloquear as escritas.
PRAGMA journal_mode = WAL;

-- Cria as tabelas de metadados espaciais:
-- spatial_ref_sys, geometry_columns, views_geometry_columns, etc.
-- O CLI spatialite já inicializa esses metadados ao abrir um banco novo;
-- por isso a chamada só executa quando eles ainda não existem.
SELECT InitSpatialMetadata(1)
WHERE NOT EXISTS (
    SELECT 1
      FROM sqlite_master
     WHERE type = 'table'
       AND name = 'spatial_ref_sys'
);

CREATE TABLE features (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- A coluna geom é criada e registrada pelo SpatiaLite.
-- SRID 4326 = WGS 84 (latitude/longitude, o mesmo sistema do GeoJSON).
-- GEOMETRY aceita ponto, linha e polígono na mesma tabela.
SELECT AddGeometryColumn('features', 'geom', 4326, 'GEOMETRY', 'XY');

-- Índice espacial R-tree sobre a coluna geom.
SELECT CreateSpatialIndex('features', 'geom');
