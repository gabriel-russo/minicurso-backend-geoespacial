-- Consultas espaciais para a demonstração em sala.
--
-- Uso:
--   spatialite data/mapa.sqlite < scripts/consultas.sql
--
-- Os cálculos de área, comprimento e distância usam o SRID 31980
-- (SIRGAS 2000 / UTM zona 20S), adequado para Rondônia. Para outra região,
-- troque pelo UTM correto ou por uma projeção equivalente.
--
-- O SRID 4326 (WGS 84) usa graus; por isso não deve ser usado diretamente
-- para calcular metros ou metros quadrados.

.mode list
.headers on

-- 1. Quantidade de geometrias por tipo
SELECT ST_GeometryType(geom) AS tipo,
       COUNT(*)             AS quantidade
  FROM features
 GROUP BY tipo
 ORDER BY quantidade DESC;

-- 2. Área dos polígonos em km²
SELECT id,
       ROUND(ST_Area(ST_Transform(geom, 31980)) / 1000000.0, 2) AS area_km2
  FROM features
 WHERE ST_GeometryType(geom) = 'POLYGON'
 ORDER BY area_km2 DESC;

-- 3. Comprimento das linhas em km
SELECT id,
       ROUND(ST_Length(ST_Transform(geom, 31980)) / 1000.0, 2) AS comprimento_km
  FROM features
 WHERE ST_GeometryType(geom) = 'LINESTRING'
 ORDER BY comprimento_km DESC;

-- 4. Geometrias que intersectam uma caixa (bbox) ao redor de Porto Velho
SELECT id,
       ST_GeometryType(geom) AS tipo
  FROM features
 WHERE ST_Intersects(
           geom,
           BuildMbr(-64.0, -9.0, -63.5, -8.5, 4326)
       )
 ORDER BY id;

-- 5. Distância de cada geometria até a UNIR (Porto Velho), em metros
WITH unir AS (
    SELECT ST_Transform(
               GeomFromText('POINT(-63.9039 -8.7612)', 4326),
               31980
           ) AS geom
)
SELECT f.id,
       ST_GeometryType(f.geom) AS tipo,
       ROUND(
           ST_Distance(ST_Transform(f.geom, 31980), unir.geom),
           1
       ) AS distancia_m
  FROM features AS f, unir
 ORDER BY distancia_m;
