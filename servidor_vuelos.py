"""Servidor local para pantalla_vuelos.html.

Sirve la página y reenvía las consultas a las APIs ADS-B (evita el bloqueo CORS del navegador).
Uso:  python servidor_vuelos.py      -> abre http://localhost:8000
Solo usa la biblioteca estándar de Python 3 (no hay que instalar nada).
"""
import http.server
import json
import pathlib
import re
import socket
import socketserver
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

PUERTO = 8000
CARPETA = pathlib.Path(__file__).resolve().parent
HTML = CARPETA / "pantalla_vuelos.html"
HTML_GITHUB = "https://raw.githubusercontent.com/matiasacc/vuelos/main/pantalla_vuelos.html"
UA = {"User-Agent": "pantalla-vuelos/1.0 (uso personal)"}

FUENTES = {
    "lol": "https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}",
    "live": "https://api.airplanes.live/v2/point/{lat}/{lon}/{nm}",
    "fi": "https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{nm}",
}
NUM = r"-?\d+(?:\.\d+)?"
RE_API = re.compile(rf"^/api/(lol|live|fi)/({NUM})/({NUM})/(\d+)$")
RE_RUTA = re.compile(r"^/route/([A-Za-z0-9]{2,8})$")
RE_LOGO = re.compile(r"^/logo/([A-Za-z]{3})$")

# Logos por código OACI de aerolínea: se prueban en orden y el primero que exista se guarda en ./logos
LOGOS_DIR = CARPETA / "logos"
FUENTES_LOGO = [
    "https://raw.githubusercontent.com/Jxck-S/airline-logos/main/flightaware_logos/{c}.png",
    "https://raw.githubusercontent.com/Jxck-S/airline-logos/main/radarbox_logos/{c}.png",
    "https://raw.githubusercontent.com/sexym0nk3y/airline-logos/main/logos/{c}.png",
]
SIN_LOGO = set()  # códigos ya buscados sin resultado (en esta sesión)


def pagina():
    """Devuelve el HTML: el de la carpeta, una copia con otro nombre, o lo baja de GitHub."""
    if HTML.exists():
        return HTML.read_bytes()
    copias = sorted(CARPETA.glob("pantalla_vuelos*.html"))
    if copias:
        return copias[0].read_bytes()
    print("  pantalla_vuelos.html no está en la carpeta: lo bajo de GitHub")
    _, datos = descargar(HTML_GITHUB)
    HTML.write_bytes(datos)
    return datos


def descargar(url, timeout=10):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


class Handler(http.server.BaseHTTPRequestHandler):
    def enviar(self, codigo, cuerpo, tipo="application/json"):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo if tipo.startswith("image/") else tipo + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = urllib.parse.urlparse(self.path).path
        if ruta in ("/", "/index.html", "/pantalla_vuelos.html"):
            try:
                return self.enviar(200, pagina(), "text/html")
            except Exception as e:
                msg = f"No encuentro pantalla_vuelos.html ni pude bajarlo de GitHub: {e}"
                return self.enviar(500, msg.encode(), "text/plain")

        m = RE_API.match(ruta)
        if m:
            fuente, lat, lon, nm = m.groups()
            url = FUENTES[fuente].format(lat=lat, lon=lon, nm=min(int(nm), 250))
            return self.reenviar(url)

        m = RE_RUTA.match(ruta)
        if m:
            return self.reenviar("https://api.adsbdb.com/v0/callsign/" + m.group(1).upper())

        m = RE_LOGO.match(ruta)
        if m:
            return self.logo(m.group(1).upper())

        self.enviar(404, b'{"error":"ruta desconocida"}')

    def logo(self, codigo):
        archivo = LOGOS_DIR / f"{codigo}.png"
        if archivo.exists():
            return self.enviar(200, archivo.read_bytes(), "image/png")
        if codigo in SIN_LOGO:
            return self.enviar(404, b"{}")
        for plantilla in FUENTES_LOGO:
            try:
                _, datos = descargar(plantilla.format(c=codigo), timeout=6)
            except Exception:
                continue
            if datos[:8] == b"\x89PNG\r\n\x1a\n":
                LOGOS_DIR.mkdir(exist_ok=True)
                archivo.write_bytes(datos)
                print(f"  logo {codigo}: {plantilla.split('/')[3]}/{plantilla.split('/')[6]}")
                return self.enviar(200, datos, "image/png")
        SIN_LOGO.add(codigo)
        self.enviar(404, b"{}")

    def reenviar(self, url):
        try:
            codigo, datos = descargar(url)
            self.enviar(codigo, datos)
        except urllib.error.HTTPError as e:
            self.enviar(e.code, json.dumps({"error": f"HTTP {e.code}"}).encode())
        except Exception as e:  # sin red, timeout, DNS, etc.
            self.enviar(502, json.dumps({"error": str(e)}).encode())

    def log_message(self, fmt, *args):
        print("  " + fmt % args)


class Servidor(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    # En Windows, SO_REUSEADDR deja abrir dos servidores en el mismo puerto y contesta el viejo
    allow_reuse_address = sys.platform != "win32"


def ip_local():
    """IP de la PC en la red de casa (la que se usa desde la TV o el celular)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no envía nada; solo elige la interfaz de salida
        return s.getsockname()[0]
    except OSError:
        return "?"
    finally:
        s.close()


if __name__ == "__main__":
    try:
        srv = Servidor(("0.0.0.0", PUERTO), Handler)
    except OSError:
        print(f"El puerto {PUERTO} está ocupado: ya hay otro servidor abierto.")
        print("Cerrá las otras ventanas de terminal (o finalizá Python en el Administrador de tareas) y volvé a abrir.")
        sys.exit(1)
    with srv:
        url = f"http://localhost:{PUERTO}"
        print(f"En esta PC:          {url}")
        print(f"Desde TV o celular:  http://{ip_local()}:{PUERTO}")
        print(f"Python usado (permitir este en el firewall): {sys.executable}")
        print("No hagas clic dentro de esta ventana (pausa el servidor). Ctrl+C para cortar.\n")
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nCerrado.")
