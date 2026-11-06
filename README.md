# SubeR · ¿Qué bondi es?

Abrí `index.html` en un navegador. El juego funciona sin instalación, servidor ni conexión. Cada partida mezcla seis colectivos, dos trenes y dos subtes o Premetro. Se sortean diez líneas distintas y se distribuye la respuesta correcta entre las cuatro posiciones.

La pista suministrada con el juego está en `audio/partida.mp3`. Empieza al tocar «Jugar», se repite durante la partida y se detiene en el resultado. El control «Música» permite silenciarla y reanudarla.

## Premio

En `premio.js` se configuran `codigoConfirmado`, `monto`, `vigencia` y `condiciones`. El resultado perfecto muestra el mensaje del premio. El código y el botón «Copiar código» aparecen cuando se carga un código confirmado. La configuración inicial deja todos los campos vacíos. Al ser un sitio estático, un código configurado queda disponible en los archivos que descarga el navegador.

## Cobertura y fuentes

- **Colectivos.** 148 líneas con tramo en CABA en la compilación de [Buenos Aires Data](https://data.buenosaires.gob.ar/es/dataset/colectivos-recorridos), [capas del AMBA](https://services1.arcgis.com/gKFHG0iKXPnKkg1l/ArcGIS/rest/services/Transporte_BuenosAires/FeatureServer) y [OpenStreetMap](https://www.openstreetmap.org/copyright). Cada línea tiene un recorrido representativo. El catálogo refleja la cobertura de las fuentes, con fechas de actualización distintas. Ocho líneas usan un trazo neutro porque falta una referencia de color.
- **Trenes.** Las [ocho líneas metropolitanas de pasajeros](https://www.argentina.gob.ar/transporte/cnrt/lineas-de-trenes-pasajeros), con trazas de OpenStreetMap y [GTFS ferroviario](https://data.buenosaires.gob.ar/dataset/trenes-gtfs). El Tren de la Costa aparece con su recorrido Maipú–Delta y el mapa del corredor, ya que circula enteramente en Provincia.
- **Subtes.** A, B, C, D, E y H, con los colores del [mapa de SBASE](https://buenosaires.gob.ar/subte/mapa-del-subte-y-combinaciones), más el ramal Centro Cívico del [Premetro](https://data.buenosaires.gob.ar/es/dataset/premetro).
- **Cartografía.** El mapa de CABA usa [calles](https://data.buenosaires.gob.ar/es/dataset/calles) y [perímetro](https://data.buenosaires.gob.ar/es/dataset/perimetro) de Buenos Aires Data. Esta cartografía está bajo [CC BY 2.5 Argentina](https://creativecommons.org/licenses/by/2.5/ar/). Los datos de OpenStreetMap están bajo [ODbL](https://www.openstreetmap.org/copyright).

Cada registro guarda línea, ramal, sentido, fuente, color y geometría. El tramo de cada servicio se recorta al perímetro de CABA, con la excepción del Tren de la Costa. Los colores de colectivos referenciados se basan en las identificaciones tradicionales de Xcolectivo o en el color registrado en OpenStreetMap.

## Regenerar el catálogo

El script `tools/preparar_mapa.py` requiere Python, Shapely, osmium y Pillow. El comando `python tools/preparar_mapa.py --help` muestra el orden de los archivos de entrada:

- GeoJSON de recorridos, calles y perímetro de Buenos Aires Data.
- Exportaciones GeoJSON WGS84 de las capas de colectivos 0, 1, 2 y 3 y la capa de subtes 5 del servicio ArcGIS del AMBA.
- GeoJSON de líneas de Premetro, ZIP de Trenes GTFS y [extracto PBF de Buenos Aires](https://download.bbbike.org/osm/bbbike/BuenosAires/).
- Carpeta de muestras opcionales de Xcolectivo, con nombre `<línea>.jpg`.
