from shapely.geometry import shape


def valid_geometry(geometry: dict) -> bool:
    try:
        geom = shape(geometry)

        if not geom.is_valid:
            return False

        return not geom.is_empty

    except:  # noqa: E722
        return False
