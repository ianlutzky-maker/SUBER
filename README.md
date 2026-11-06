# SubeR · ¿Qué bondi es?

Abrí `index.html` en un navegador. El juego funciona sin instalación, servidor ni conexión. En cada partida se sortean diez líneas distintas del catálogo y se distribuye la respuesta correcta entre las cuatro posiciones.

## Premio

En `premio.js` se configuran `codigoConfirmado`, `monto`, `vigencia` y `condiciones`. El resultado perfecto muestra el mensaje del premio. El código y el botón «Copiar código» aparecen cuando se carga un código confirmado. La configuración inicial deja todos los campos vacíos. Al ser un sitio estático, un código configurado queda disponible en los archivos que descarga el navegador.

## Datos cartográficos

- [Recorridos de colectivos · Buenos Aires Data](https://data.buenosaires.gob.ar/es/dataset/colectivos-recorridos). Cada desafío conserva línea, ramal, sentido, origen, destino y fuente. La geometría se guarda como GeoJSON en longitud y latitud, con las coordenadas recortadas al [perímetro de CABA](https://data.buenosaires.gob.ar/es/dataset/perimetro).
- [Callejero · Buenos Aires Data](https://data.buenosaires.gob.ar/es/dataset/calles). El mapa usa geometrías simplificadas y omite las etiquetas. La cartografía de Buenos Aires Data tiene licencia [CC BY 2.5 Argentina](https://creativecommons.org/licenses/by/2.5/ar/).
- Los colores se basan en las identificaciones tradicionales de cada línea documentadas por Xcolectivo. Los tonos se ajustaron para distinguir el trazado sobre el fondo blanco. Cada registro guarda su referencia.

Para regenerar `data.js`, descargá los GeoJSON de [recorridos](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-recorridos/recorrido-colectivos.geojson), [calles](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/calles/callejero.geojson) y [perímetro](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/perimetro/perimetro.geojson). Con Python y Shapely instalados, ejecutá:

```sh
python tools/preparar_mapa.py recorrido-colectivos.geojson callejero.geojson perimetro.geojson data.js
```
