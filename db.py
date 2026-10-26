"""Camada de acesso ao banco espacial SQLite + SpatiaLite."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "mapa.sqlite"


def conectar() -> sqlite3.Connection:
    """Abre uma conexão com o banco e carrega a extensão SpatiaLite.

    A extensão é carregada em TODA conexão nova. Isso é uma característica
    do SQLite: cada conexão começa sem as funções espaciais.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    conn.load_extension("mod_spatialite")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def abrir_conexao() -> Iterator[sqlite3.Connection]:
    """Abre, confirma (commit) e fecha a conexão; desfaz em caso de erro."""
    conn = conectar()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def verificar_banco() -> None:
    """Falha cedo, com uma mensagem útil, se o banco não estiver pronto."""
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Banco não encontrado em {DB_PATH}.\n"
            "Crie o banco com: spatialite data/mapa.sqlite < schema.sql"
        )

    with abrir_conexao() as conn:
        registro = conn.execute(
            """
            SELECT 1
              FROM geometry_columns
             WHERE f_table_name = 'features'
               AND f_geometry_column = 'geom'
            """
        ).fetchone()

    if registro is None:
        raise RuntimeError(
            "A tabela espacial features/geom não foi encontrada.\n"
            "Recrie o banco com: rm -f data/mapa.sqlite && "
            "spatialite data/mapa.sqlite < schema.sql"
        )


def _row_para_feature(row: sqlite3.Row) -> dict[str, Any]:
    """Converte uma linha do banco em um GeoJSON Feature."""
    return {
        "type": "Feature",
        "id": row["id"],
        "geometry": json.loads(row["geojson"]),
        "properties": {
            "id": row["id"],
            "criado_em": row["criado_em"],
        },
    }


def listar_features() -> list[dict[str, Any]]:
    with abrir_conexao() as conn:
        rows = conn.execute(
            """
            SELECT id, AsGeoJSON(geom) AS geojson, criado_em
              FROM features
             ORDER BY id
            """
        ).fetchall()

    return [_row_para_feature(row) for row in rows]


def criar_feature(wkt: str) -> dict[str, Any]:
    """Insere uma geometria a partir de WKT e devolve o Feature criado."""
    with abrir_conexao() as conn:
        cursor = conn.execute(
            "INSERT INTO features (geom) VALUES (GeomFromText(?, 4326))",
            (wkt,),
        )
        feature_id = cursor.lastrowid

        row = conn.execute(
            """
            SELECT id, AsGeoJSON(geom) AS geojson, criado_em
              FROM features
             WHERE id = ?
            """,
            (feature_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError("Falha ao ler a geometria recém-criada.")

    return _row_para_feature(row)


def excluir_feature(feature_id: int) -> bool:
    """Remove a geometria. Retorna False se o id não existir."""
    with abrir_conexao() as conn:
        cursor = conn.execute("DELETE FROM features WHERE id = ?", (feature_id,))

    return cursor.rowcount > 0
