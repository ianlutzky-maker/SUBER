"""Genera data.js a partir de GeoJSON, un extracto de OSM y el GTFS ferroviario."""
import argparse
from collections import defaultdict, Counter
import csv
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

import osmium
from PIL import Image
from shapely import line_merge
from shapely.geometry import LineString, MultiLineString, Point, shape
from shapely.validation import make_valid

LAYERS = "https://services1.arcgis.com/gKFHG0iKXPnKkg1l/ArcGIS/rest/services/Transporte_BuenosAires/FeatureServer"
CITY_BUSES = "https://data.buenosaires.gob.ar/es/dataset/colectivos-recorridos"
PREMETRO = "https://data.buenosaires.gob.ar/es/dataset/premetro"
SUBWAY_MAP = "https://buenosaires.gob.ar/subte/mapa-del-subte-y-combinaciones"
RAIL_GTFS = "https://data.buenosaires.gob.ar/dataset/trenes-gtfs"
CANCELLED = {5, 6, 23, 36, 75, 90, 99, 104, 112, 141, 165, 175}
BUS_COLORS = {
    12: "#b8202c", 26: "#233fe0", 34: "#201261", 39: "#986000",
    42: "#a88a04", 64: "#173c87", 68: "#0962df", 107: "#176821",
    109: "#c92326", 118: "#173982", 132: "#3123c7", 151: "#a02630",
}
TRAIN_RELATIONS = {
    129384: "Belgrano Norte", 1889579: "Urquiza", 4572178: "Mitre",
    1878867: "Sarmiento", 3738002: "Roca", 1894770: "San Martín",
    3443503: "Belgrano Sur",
}
SUBWAY_INFO = {
    "A": ("Plaza de Mayo", "San Pedrito", (-58.37, -34.608), "#087ca2"),
    "B": ("Leandro N. Alem", "Juan Manuel de Rosas", (-58.37, -34.603), "#c82135"),
    "C": ("Retiro", "Constitución", (-58.375, -34.592), "#1254a1"),
    "D": ("Catedral", "Congreso de Tucumán", (-58.374, -34.607), "#168045"),
    "E": ("Retiro", "Plaza de los Virreyes", (-58.374, -34.592), "#773694"),
    "H": ("Facultad de Derecho", "Hospitales", (-58.393, -34.583), "#a47700"),
}
ROAD_TYPES = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "living_street"}
LARGE_ROADS = {"motorway", "trunk", "primary"}


def features(file):
    return json.loads(file.read_text())["features"]


def lines(geometry):
    if geometry.geom_type == "LineString" and not geometry.is_empty:
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from lines(part)


def clip_in_order(line, city):
    if city is None:
        return [line]
    parts = []
    for segment in lines(line.intersection(city)):
        start = line.project(Point(segment.coords[0]))
        end = line.project(Point(segment.coords[-1]))
        parts.append((min(start, end), segment if start <= end else segment.reverse()))
    return [segment for _, segment in sorted(parts, key=lambda item: item[0])]


def svg_path(coords):
    return "M" + " ".join(f"{(lon + 58.55) * 91650:.1f},{(-34.51 - lat) * 111320:.1f}" for lon, lat in coords)


def route(modo, linea, ramal, sentido, segments, color, source, **extra):
    coordinates = [
        [[round(lon, 7), round(lat, 7)] for lon, lat in section.simplify(.000012).coords]
        for section in segments if section.length > .000012
    ]
    return dict(
        modo=modo, linea=linea, ramal=ramal, sentido=sentido, color=color,
        fuente=source, demostracion=False, **extra,
        geometry=dict(type="MultiLineString", coordinates=coordinates),
    )


def bus_color(number, folder, osm_color):
    source = f"https://www.xcolectivo.com.ar/imagenes/colectivos/identificador/linea{number}.jpg"
    if number in BUS_COLORS:
        return BUS_COLORS[number], source
    try:
        with Image.open(folder / f"{number}.jpg") as sample:
            swatch = sample.convert("RGB").resize((100, 100))
        pixels = [swatch.getpixel((x, y)) for x in (9, 90) for y in range(34, 90)]
        buckets = Counter(tuple((v // 24) * 24 for v in rgb) for rgb in pixels)
        color = next((rgb for rgb, _ in buckets.most_common() if max(rgb) - min(rgb) >= 35), None)
        if color is None:
            strips = [swatch.getpixel((8, y)) for y in range(12, 30)]
            color = next((rgb for rgb in strips if max(rgb) - min(rgb) >= 75), None)
        if color:
            r, g, b = color
            brightness = .2126 * r + .7152 * g + .0722 * b
            factor = min(1, 136 / max(brightness, 1))
            return "#" + "".join(f"{round(v * factor):02x}" for v in color), source
    except OSError:
        pass
    return (osm_color, "Color de la relación de OpenStreetMap") if re.fullmatch(r"#[0-9a-fA-F]{6}", osm_color) else ("#485b70", None)


def extract_osm(file):
    routes = {}
    way_ids = set()
    for relation in osmium.FileProcessor(file, osmium.osm.RELATION):
        tags = dict(relation.tags)
        match = re.match(r"^\d+", tags.get("ref", ""))
        if relation.id not in TRAIN_RELATIONS and (tags.get("route") != "bus" or not match):
            continue
        number = int(match[0]) if tags.get("route") == "bus" else None
        ways = [m.ref for m in relation.members if m.type == "w" and m.role in ("", "forward", "backward")]
        if not ways:
            continue
        routes[relation.id] = (number, tags, ways)
        way_ids.update(ways)

    track, minor, major = {}, [], []
    for way in osmium.FileProcessor(file).with_locations():
        if not isinstance(way, osmium.osm.Way):
            continue
        road = way.tags.get("highway")
        if way.id not in way_ids and road not in ROAD_TYPES:
            continue
        if any(not n.location.valid() for n in way.nodes):
            continue
        coords = [(n.lon, n.lat) for n in way.nodes]
        if way.id in way_ids:
            track[way.id] = coords
        if road in ROAD_TYPES and any(-58.57 < x < -58.446 and -34.52 < y < -34.398 for x, y in coords):
            group = major if road in LARGE_ROADS else minor
            group.append(svg_path(LineString(coords).simplify(.000019).coords))
    return routes, track, {"streets": "".join(minor), "avenues": "".join(major)}


def ordered_ways(ids, track):
    sections = []
    for i, way_id in enumerate(ids):
        coords = track.get(way_id)
        if not coords or len(coords) < 2:
            continue
        if sections and sections[-1][-1] == coords[-1]:
            coords = coords[::-1]
        elif not sections and i + 1 < len(ids):
            following = track.get(ids[i + 1], [])
            if following and coords[0] in (following[0], following[-1]):
                coords = coords[::-1]
        if sections and sections[-1][-1] == coords[0]:
            sections[-1].extend(coords[1:])
        else:
            sections.append(list(coords))
    return [LineString(coords) for coords in sections]


def collect_buses(args, city, osm_routes, track):
    best = {}

    def consider(number, ramal, sentido, parts, priority, source, osm_color="", **extra):
        if number in CANCELLED:
            return
        clipped = [section for line in parts for section in clip_in_order(line, city)]
        length = sum(line.length for line in clipped)
        rank = (priority, length)
        if length < .00035 or (number in best and rank <= best[number][0]):
            return
        color, color_source = bus_color(number, args.colores, osm_color)
        best[number] = (rank, route(
            "colectivo", number, str(ramal), str(sentido), clipped, color, source,
            fuenteColor=color_source, referenciaColor="Color tradicional ajustado para contraste" if color_source else "Trazo neutro",
            **extra,
        ))

    for priority, file, source in (
        (4, args.colectivos, CITY_BUSES),
        (1, args.arc_caba, f"{LAYERS}/0"),
        (1, args.arc_provincial, f"{LAYERS}/1"),
        (1, args.arc_nacional, f"{LAYERS}/2"),
        (1, args.arc_municipal, f"{LAYERS}/3"),
    ):
        for feature in features(file):
            p = {k.lower(): v for k, v in feature["properties"].items()}
            number = str(p.get("linea"))
            if not number.isdigit():
                continue
            consider(int(number), p.get("recorrido", p.get("ramal")), p.get("sentido"),
                     lines(shape(feature["geometry"])), priority, source,
                     id=str(p.get("l_r_s", p.get("fid"))), origen=p.get("desde"), destino=p.get("hasta"))

    for identifier, (number, tags, ids) in osm_routes.items():
        if number is None or number in best and best[number][0][0] == 4:
            continue
        name = tags.get("name", tags.get("ref", ""))
        origin, destination = tags.get("from"), tags.get("to")
        consider(number, name, f"{origin} → {destination}" if origin and destination else name,
                 ordered_ways(ids, track), 2, f"https://www.openstreetmap.org/relation/{identifier}",
                 tags.get("colour", ""), id=str(identifier), origen=origin, destino=destination)
    return [best[number][1] for number in sorted(best)]


def collect_trains(args, city, osm_routes, track):
    result = []
    for identifier, name in TRAIN_RELATIONS.items():
        _, tags, ways = osm_routes[identifier]
        sections = [section for line in ordered_ways(ways, track) for section in clip_in_order(line, city)]
        origin, destination = tags["from"], tags["to"]
        result.append(route(
            "tren", name, f"{origin} – {destination}", f"Hacia {destination}", sections,
            "#bf292e" if name in {"Belgrano Norte", "Urquiza"} else "#137dab",
            f"https://www.openstreetmap.org/relation/{identifier}",
            origen=origin, destino=destination,
        ))

    with ZipFile(args.trenes) as feed:
        def table(name):
            return csv.DictReader(io.TextIOWrapper(feed.open(name + ".txt"), encoding="utf-8-sig"))
        service = next(r for r in table("routes") if r["route_long_name"].startswith("Tren de la Costa"))
        trip = next(t for t in table("trips") if t["route_id"] == service["route_id"] and t["direction_id"] == "0")
        points = sorted(
            (int(p["shape_pt_sequence"]), float(p["shape_pt_lon"]), float(p["shape_pt_lat"]))
            for p in table("shapes") if p["shape_id"] == trip["shape_id"]
        )
    result.append(route(
        "tren", "Tren de la Costa", "Maipú – Delta", "Hacia Delta",
        [LineString([(lon, lat) for _, lon, lat in points])], "#137dab", RAIL_GTFS,
        origen="Maipú", destino="Delta", mapa="costa",
    ))
    return result


def orient_sections(parts, start):
    remaining, oriented = list(parts), []
    while remaining:
        def distances(part):
            return start.distance(Point(part.coords[0])), start.distance(Point(part.coords[-1]))
        part = min(remaining, key=lambda line: min(distances(line)))
        remaining.remove(part)
        first, last = distances(part)
        if last < first:
            part = part.reverse()
        oriented.append(part)
        start = Point(part.coords[-1])
    return oriented


def collect_subways(args):
    segments = defaultdict(list)
    for f in features(args.subte):
        label = f["properties"]["lineasub"].split()[-1]
        segments[label].extend(lines(shape(f["geometry"])))
    result = []
    for name, (origin, destination, point, color) in SUBWAY_INFO.items():
        parts = orient_sections(lines(line_merge(MultiLineString(segments[name]))), Point(point))
        result.append(route("subte", name, f"{origin} – {destination}", f"Hacia {destination}",
                            parts, color, f"{LAYERS}/5", origen=origin, destino=destination, fuenteColor=SUBWAY_MAP))

    feature = next(f for f in features(args.premetro) if f["properties"]["ramal"] == "Int Saguier - Centro Civico")
    parts = orient_sections(lines(shape(feature["geometry"])), Point(-58.4616, -34.6432))
    result.append(route("subte", "Premetro", feature["properties"]["ramal"], "Hacia Centro Cívico",
                        parts, "#b95810", PREMETRO, fuenteColor=SUBWAY_MAP))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("colectivos", "arc_caba", "arc_provincial", "arc_nacional", "arc_municipal", "calles",
                 "perimetro", "subte", "premetro", "trenes", "osm", "colores", "salida"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()

    city = make_valid(shape(features(args.perimetro)[0]["geometry"]))
    boundary = svg_path(city.exterior.simplify(.000015).coords) + "Z"
    minor, major = [], []
    for feature in features(args.calles):
        group = major if feature["properties"]["tipo_c"] in {"AVENIDA", "AUTOPISTA"} else minor
        group.append(svg_path(shape(feature["geometry"]).simplify(.000015).coords))

    osm_routes, track, coast_map = extract_osm(args.osm)
    routes = collect_buses(args, city, osm_routes, track) + collect_trains(args, city, osm_routes, track) + collect_subways(args)
    keys = {(r["modo"], r["linea"]) for r in routes}
    if len(keys) != len(routes) or any(not r["geometry"]["coordinates"] for r in routes):
        raise ValueError("El catálogo tiene líneas duplicadas o sin geometría")
    print(dict(Counter(r["modo"] for r in routes)))
    data = dict(routes=routes, streets="".join(minor), avenues="".join(major), boundary=boundary, coastMap=coast_map)
    args.salida.write_text("window.suberData = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")


if __name__ == "__main__":
    main()
