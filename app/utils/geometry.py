from shapely.geometry import shape


def valid_geometry(geometry: dict) -> bool:
    try:
        geom = shape(geometry)

        if not geom.is_valid:
            return False

        if geom.is_empty:
            return False

        return True
    except Exception:
        return False
