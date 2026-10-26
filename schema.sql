-- Estrutura do banco espacial do mapa colaborativo.
--
-- https://www.gaia-gis.it/gaia-sins/spatialite-cookbook-5/cookbook_topics.03.html#topic_Creating_a_new_Geometry_column
--
-- Para criar do zero:
--   spatialite data/mapa.sqlite < schema.sql
-- ====================================================================================================================

-- WAL permite ler o banco com a API rodando, sem bloquear as escritas.
PRAGMA journal_mode = WAL;

CREATE TABLE desenho (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    criado_por TEXT NOT NULL DEFAULT 'Anon',
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

SELECT AddGeometryColumn(
    'desenho', -- nome da tabela (ALTER TABLE desenho)
    'geom', -- Nome da coluna (ADD COLUMN geom)
    4326, -- SRID
    'GEOMETRY', -- Tipo da geometria
    'XY' -- Geometria do tipo 2D
);
