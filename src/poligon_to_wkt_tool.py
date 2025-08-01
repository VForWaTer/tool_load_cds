import sys
import json
from shapely.geometry import Polygon, shape
from json2args import get_parameter
from json2args.logger import logger

class ParamsWKT:
    coordinates: list[list[float]]  # Optional: list of [lon, lat] pairs
    geojson: str                    # Optional: GeoJSON string


def generate_polygon_wkt(kwargs: ParamsWKT) -> str:
    """
    Generate a WKT polygon string from either a list of coordinates or a GeoJSON.
    """
    coords = getattr(kwargs, 'coordinates', None)
    geojson_str = getattr(kwargs, 'geojson', None)

    if coords and geojson_str:
        logger.error("Provide only one of 'coordinates' or 'geojson'.")
        sys.exit(1)

    if coords:
        try:
            geom = Polygon(coords)
        except Exception as e:
            logger.error(f"Invalid coordinates: {e}")
            sys.exit(1)
    elif geojson_str:
        try:
            geo = json.loads(geojson_str)
            geom = shape(geo)
        except Exception as e:
            logger.error(f"Invalid GeoJSON: {e}")
            sys.exit(1)
    else:
        logger.error("Must provide either 'coordinates' or 'geojson'.")
        sys.exit(1)

    wkt_str = geom.wkt
    print(wkt_str)
    return wkt_str


if __name__ == '__main__':
    # Parse parameters from JSON/CLI
    kwargs = get_parameter(typed=True)
    generate_polygon_wkt(kwargs)
