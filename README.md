# SubeR · ¿Qué bondi es?

Abrí `index.html` en un navegador. El juego funciona sin instalación, servidor ni conexión. Cada partida mezcla seis colectivos, dos trenes y dos subtes o Premetro. Se sortean diez líneas distintas y se distribuye la respuesta correcta entre las cuatro posiciones.

La pista suministrada con el juego está en `audio/partida.mp3`. Empieza al tocar «Jugar», se repite durante la partida y se detiene en el resultado. El control «Música» permite silenciarla y reanudarla.

## Premio

Cada acierto suma 10 puntos porcentuales de descuento. El resultado va de 0% OFF a 100% OFF, con un remate distinto para cada puntaje. En `premio.js`, `codigosPorDescuento` permite asociar un código confirmado a cada porcentaje, por ejemplo `{ 20: "CODIGO20" }`. El campo `codigoConfirmado` sirve como código alternativo para el 100%. También se pueden configurar `vigencia` y `condiciones`. Un código aparece solo cuando está configurado para el descuento obtenido. Los códigos cargados en el sitio estático quedan disponibles en los archivos que descarga el navegador.

## Cobertura y fuentes

- **Colectivos.** 127 líneas con un tramo significativo en CABA en la compilación de [Buenos Aires Data](https://data.buenosaires.gob.ar/es/dataset/colectivos-recorridos), [capas del AMBA](https://services1.arcgis.com/gKFHG0iKXPnKkg1l/ArcGIS/rest/services/Transporte_BuenosAires/FeatureServer) y [OpenStreetMap](https://www.openstreetmap.org/copyright). Cada línea tiene un recorrido representativo. El catálogo refleja la cobertura de las fuentes, con fechas de actualización distintas. Algunas líneas usan un trazo neutro porque falta una referencia de color.
- **Trenes.** Las siete [líneas metropolitanas de pasajeros](https://www.argentina.gob.ar/transporte/cnrt/lineas-de-trenes-pasajeros) que pasan por CABA, con trazas de OpenStreetMap. El Tren de la Costa queda fuera del sorteo porque circula enteramente en Provincia.
- **Subtes.** A, B, C, D, E y H, con los colores del [mapa de SBASE](https://buenosaires.gob.ar/subte/mapa-del-subte-y-combinaciones), más el ramal Centro Cívico del [Premetro](https://data.buenosaires.gob.ar/es/dataset/premetro).
- **Cartografía.** El mapa de CABA usa [calles](https://data.buenosaires.gob.ar/es/dataset/calles) y [perímetro](https://data.buenosaires.gob.ar/es/dataset/perimetro) de Buenos Aires Data. Esta cartografía está bajo [CC BY 2.5 Argentina](https://creativecommons.org/licenses/by/2.5/ar/). Los datos de OpenStreetMap están bajo [ODbL](https://www.openstreetmap.org/copyright).

Cada registro guarda línea, ramal, sentido, fuente, color y geometría. El encuadre inicial se centra en el tramo porteño. El botón «Ver recorrido entero» encuadra también los tramos exteriores, y «Centrar en CABA» recupera la vista inicial. Entran al sorteo los recorridos con al menos 1 km en CABA y, además, con al menos 12% de su longitud o 2,5 km dentro de la ciudad. El callejero termina en el límite de la ciudad y los tramos exteriores se dibujan sobre gris liso. Los colores de colectivos referenciados se basan en las identificaciones tradicionales de Xcolectivo o en el color registrado en OpenStreetMap.

## Regenerar el catálogo

El script `tools/preparar_mapa.py` requiere Python, Shapely, osmium y Pillow. El comando `python tools/preparar_mapa.py --help` muestra el orden de los archivos de entrada:

- GeoJSON de recorridos, calles y perímetro de Buenos Aires Data.
- Exportaciones GeoJSON WGS84 de las capas de colectivos 0, 1, 2 y 3 y la capa de subtes 5 del servicio ArcGIS del AMBA.
- GeoJSON de líneas de Premetro, ZIP de Trenes GTFS y [extracto PBF de Buenos Aires](https://download.bbbike.org/osm/bbbike/BuenosAires/).
- Carpeta de muestras opcionales de Xcolectivo, con nombre `<línea>.jpg`.
- Carpeta de relaciones completas de OpenStreetMap, con nombre `full-<id>.json`, descargadas desde `https://api.openstreetmap.org/api/0.6/relation/<id>/full.json` para los trenes y las relaciones de colectivo incompletas en el extracto.
