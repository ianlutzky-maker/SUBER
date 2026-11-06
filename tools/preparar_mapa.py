"""Genera data.js con los tres GeoJSON de Buenos Aires Data. Requiere Shapely."""
import argparse
import json
from pathlib import Path

from shapely.geometry import LineString, Point, shape
from shapely.validation import make_valid

COLORS = {
    12: "#b8202c", 26: "#233fe0", 34: "#201261", 39: "#986000",
    42: "#a88a04", 64: "#173c87", 68: "#0962df", 107: "#176821",
    109: "#c92326", 118: "#173982", 132: "#3123c7", 151: "#a02630",
}
SOURCE = "https://data.buenosaires.gob.ar/es/dataset/colectivos-recorridos"


def features(file):
    return json.loads(file.read_text())["features"]


def lines(geometry):
    if geometry.geom_type == "LineString" and not geometry.is_empty:
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from lines(part)


def clip_in_order(line, city):
    parts = []
    for segment in lines(line.intersection(city)):
        coords = list(segment.coords)
        start = line.project(Point(coords[0]))
        end = line.project(Point(coords[-1]))
        parts.append((min(start, end), coords if start <= end else coords[::-1]))
    return [coords for _, coords in sorted(parts, key=lambda item: item[0])]


def svg_path(coords):
    return "M" + " ".join(f"{(lon + 58.55) * 91650:.1f},{(-34.51 - lat) * 111320:.1f}" for lon, lat in coords)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("recorridos", "calles", "perimetro", "salida"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()

    city = make_valid(shape(features(args.perimetro)[0]["geometry"]))
    boundary = svg_path(city.exterior.simplify(0.000015).coords) + "Z"
    minor, major = [], []
    for feature in features(args.calles):
        properties = feature["properties"]
        group = major if properties["tipo_c"] in {"AVENIDA", "AUTOPISTA"} else minor
        group.append(svg_path(shape(feature["geometry"]).simplify(0.000015).coords))

    routes = []
    for feature in features(args.recorridos):
        p = feature["properties"]
        if not p["linea"].isdigit():
            continue
        number = int(p["linea"])
        if number not in COLORS or p["recorrido"] != "A" or p["sentido"] != "IDA":
            continue
        coordinates = [
            [[round(lon, 7), round(lat, 7)] for lon, lat in section]
            for line in lines(shape(feature["geometry"]))
            for section in clip_in_order(line, city)
        ]
        if not coordinates:
            raise ValueError(f"Recorrido sin tramo en CABA: {p['l_r_s']}")
        routes.append(dict(
            linea=number, ramal=p["recorrido"], sentido=p["sentido"],
            origen=p["desde"], destino=p["hasta"], id=p["l_r_s"],
            geometry=dict(type="MultiLineString", coordinates=coordinates),
            color=COLORS[number], fuente=SOURCE,
            fuenteColor=f"https://www.xcolectivo.com.ar/colectivo/recorridos.php?linea={number}",
            referenciaColor="Color tradicional, ajustado para contraste", demostracion=False,
        ))
    if len(routes) < 10 or len({r["linea"] for r in routes}) != len(routes):
        raise ValueError("El catálogo debe tener al menos diez líneas únicas")
    data = dict(routes=routes, streets="".join(minor), avenues="".join(major), boundary=boundary)
    args.salida.write_text("window.suberData = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")


if __name__ == "__main__":
    main()
