"""
Verifica se o Python e o banco estão prontos para o minicurso.
"""

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "app" / "database" / "mapa.sqlite"


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
    except:
        return falhar(
            "não foi possível carregar a extensão mod_spatialite.\n"
            "No Ubuntu/WSL: sudo apt install -y libsqlite3-mod-spatialite"
        )

    if not DB_PATH.exists():
        return falhar(
            f"banco não encontrado em {DB_PATH}.\n"
            "Crie o banco com: spatialite app/database/mapa.sqlite < scripts/estrutura_banco_de_dados.sql"
        )

    # 2. O banco precisa ter a tabela espacial criada pelo schema.sql.
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    conn.load_extension("mod_spatialite")

    registro = conn.execute(
        """
        SELECT srid
          FROM geometry_columns
         WHERE f_table_name = 'tb_desenhos'
           AND f_geometry_column = 'geom'
        """
    ).fetchone()

    if registro is None:
        conn.close()
        return falhar(
            "a tabela espacial tb_desenhos/geom não existe.\n"
            "Recrie o banco com: rm -f app/database/mapa.sqlite && "
            "spatialite app/database/mapa.sqlite < scripts/estrutura_banco_de_dados.sql"
        )

    indice = conn.execute("SELECT CheckSpatialIndex('tb_desenhos', 'geom')").fetchone()[
        0
    ]

    total = conn.execute("SELECT COUNT(*) FROM tb_desenhos").fetchone()[0]

    conn.close()

    if indice != 1:
        return falhar("Alerta: o índice espacial não está ativo.")

    print(f"OK  tabela tb_desenhos/geom com SRID {registro[0]}")
    print("OK  índice espacial R-tree ativo")
    print(f"OK  {total} geometria(s) no banco")
    print("\nTudo pronto. Rode: uv run fastapi dev")
    return 0


if __name__ == "__main__":
    sys.exit(main())
