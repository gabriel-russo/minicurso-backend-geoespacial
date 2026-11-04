"""
Camada de gerenciamento do banco de dados espacial SpatiaLite.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

from aiosqlite import Connection, Row, connect

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "mapa.sqlite"


async def acquire_connection() -> AsyncGenerator[Connection]:
    async with connect(DB_PATH) as conn:
        # A extensão é carregada em TODA conexão nova. Isso é uma característica
        # do SQLite: cada conexão começa sem as funções espaciais.
        await conn.enable_load_extension(True)
        await conn.load_extension("mod_spatialite")
        conn.row_factory = Row
        yield conn


async def database_checkup() -> None:
    """Falha cedo, com uma mensagem útil, se o banco não estiver pronto."""
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Banco não encontrado em {DB_PATH}.\n"
            "Crie o banco com: spatialite app/database/mapa.sqlite < estrutura_banco_de_dados.sql"
        )

    async with connect(DB_PATH) as conn, conn.cursor() as cur:
        await cur.execute(
            """
                SELECT 1
                  FROM geometry_columns
                 WHERE f_table_name = 'tb_desenhos'
                   AND f_geometry_column = 'geom'
                """
        )

        registro = await cur.fetchone()

    if registro is None:
        raise RuntimeError(
            "A tabela espacial tb_desenhos/geom não foi encontrada. Refaça o processo de criação do banco."
        )
