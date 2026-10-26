"""Verifica se o Python e o banco estão prontos para o minicurso."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mapa.sqlite"


def falhar(mensagem: str) -> int:
    print(f"\nERRO: {mensagem}\n")
    return 1


def main() -> int:
    # 1. A extensão precisa carregar em uma conexão Python.
    try:
        conn = sqlite3.connect(":memory:")
        conn.enable_load_extension(True)
        conn.load_extension("mod_spatialite")

        versao = conn.execute("SELECT spatialite_version()").fetchone()[0]
        geos = conn.execute("SELECT geos_version()").fetchone()[0]
        print(f"OK  SpatiaLite {versao} carregado no Python")
        print(f"OK  GEOS {geos}")
        conn.close()
    except Exception:
        return falhar(
            "não foi possível carregar a extensão mod_spatialite.\n"
            "No Ubuntu/WSL: sudo apt install -y libsqlite3-mod-spatialite"
        )

    if not DB_PATH.exists():
        return falhar(
            f"banco não encontrado em {DB_PATH}.\n"
            "Crie o banco com: spatialite data/mapa.sqlite < schema.sql"
        )

    # 2. O banco precisa ter a tabela espacial criada pelo schema.sql.
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    conn.load_extension("mod_spatialite")

    registro = conn.execute(
        """
        SELECT srid
          FROM geometry_columns
         WHERE f_table_name = 'features'
           AND f_geometry_column = 'geom'
        """
    ).fetchone()

    if registro is None:
        conn.close()
        return falhar(
            "a tabela espacial features/geom não existe.\n"
            "Recrie o banco com: rm -f data/mapa.sqlite && "
            "spatialite data/mapa.sqlite < schema.sql"
        )

    indice = conn.execute("SELECT CheckSpatialIndex('features', 'geom')").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM features").fetchone()[0]
    conn.close()

    if indice != 1:
        return falhar(
            "o índice espacial não está ativo.\n"
            "Recrie o banco com: rm -f data/mapa.sqlite && "
            "spatialite data/mapa.sqlite < schema.sql"
        )

    print(f"OK  tabela features/geom com SRID {registro[0]}")
    print("OK  índice espacial R-tree ativo")
    print(f"OK  {total} geometria(s) no banco")
    print("\nTudo pronto. Rode: uv run uvicorn main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
