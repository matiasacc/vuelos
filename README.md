# Vuelos en mi zona

Pantalla con los aviones que pasan dentro de un radio alrededor de tu ubicación o de un aeropuerto. Tiene un panel con el vuelo que entra a la zona (logo, aerolínea, ruta, avión, altitud, V/S, GS, rumbo), un mapa estilo Navigation Display (anillos de distancia, rosa de rumbos, etiquetas tipo radar con estela) y listas separadas por fase de vuelo.

## Uso

```
python servidor_vuelos.py
```

- En la PC: `http://localhost:8000`
- Desde la TV o el celular: la dirección "Desde TV o celular" que imprime el servidor (`http://<IP de la PC>:8000`), en la misma red.

Requiere Python 3 (solo biblioteca estándar) y conexión a internet. Si la TV o el celular no cargan, revisar el firewall de Windows: habilitar Python (o el puerto TCP 8000) en el perfil de red que corresponda.

## Archivos

| Archivo | Función |
|---|---|
| `pantalla_vuelos.html` | Página (panel, mapa Leaflet, filtros, listas, configuración) |
| `servidor_vuelos.py` | Sirve la página y reenvía las consultas a las APIs (evita el bloqueo CORS del navegador); descarga y guarda en caché los logos en `logos/` |

## Fuentes de datos

| Dato | Fuente |
|---|---|
| Posiciones ADS-B | adsb.lol → airplanes.live → adsb.fi (en ese orden si una falla) |
| Ruta y aerolínea | adsbdb.com (por indicativo; no siempre está) |
| Logos | repositorio Jxck-S/airline-logos (GitHub), por código OACI |
| Mapa base | © OpenStreetMap, © CARTO (dark) |

## Criterios

- **Aerolínea:** prefijo OACI de 3 letras del indicativo (ARG, FBZ, JAT…), salvo que adsbdb dé el nombre.
- **Fase:**
  - Despegue: V/S > +300 ft/min y altitud < 15.000 ft.
  - Aterrizaje: V/S < −300 ft/min y altitud < 15.000 ft.
  - En tierra: el transpondedor informa `ground`.
  - En ruta: el resto.
- **Distancia:** Haversine con R = 6371 km.

## Limitaciones

- La fase sale solo del régimen vertical: un avión que desciende hacia otro aeródromo cercano también figura como aterrizaje.
- La cobertura depende de los receptores de las redes comunitarias en la zona. Los aviones sin ADS-B no aparecen.
- Los logos son marcas de cada aerolínea: el proyecto es para uso personal.
