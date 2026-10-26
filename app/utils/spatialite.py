from json import loads as json_loads
from typing import Any

from aiosqlite import Row


def row_to_feature(row: Row) -> dict[str, Any]:
    """
    Converte uma linha do banco em um GeoJSON Feature.
    """
    data = dict(row)
    id = data.pop("id")
    geometry = json_loads(data.pop("geom"))
    return {
        "type": "Feature",
        "id": id,
        "geometry": geometry,
        "properties": {"id": id, **data},
    }
