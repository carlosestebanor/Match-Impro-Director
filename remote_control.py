"""
MATCH DE IMPRO - DIRECTOR :: MÓDULO DE CONTROL REMOTO
------------------------------------------------------------------------------
Servidor HTTP ligero (solo librería estándar de Python) que publica un "mando a
distancia" web. Permite manejar cronómetro, puntos, faltas y efectos de sonido
desde un celular o tablet conectado a la misma red WiFi que el computador del
operador.

Diseño:
  - El servidor corre en un hilo aparte para no congelar la interfaz Tkinter.
  - Tkinter NO es thread-safe: por eso este módulo nunca toca widgets. Solo
    ENCOLA comandos que la aplicación principal ejecuta en su propio hilo.
  - El acceso está protegido por un PIN numérico que se muestra en el panel.

Autor: Corporación Acción Impro
Ubicación: Medellín, Colombia
Año: 2026
Licencia: Creative Commons Atribución 4.0 Internacional (CC BY 4.0)
------------------------------------------------------------------------------
"""

import json
import random
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Tamaño máximo aceptado en un POST (evita que un cliente nos mande basura enorme)
MAX_BODY = 8 * 1024

# Pausa aplicada ante un PIN incorrecto (frena intentos por fuerza bruta)
PENALIZACION_PIN = 0.5


def obtener_ip_local():
    """Devuelve la IP de la máquina en la red local (la que verá el celular)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No se envía tráfico real: solo se usa para saber por qué interfaz saldríamos.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        s.close()


def generar_pin():
    """PIN de 6 dígitos para emparejar el celular con el panel."""
    return f"{random.randint(0, 999999):06d}"


# ==============================================================================
# PÁGINA WEB DEL MANDO (se sirve completa, sin recursos externos)
# ==============================================================================
PAGINA_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#111111">
<title>Match Impro - Control Remoto</title>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body {
    margin: 0; padding: 12px 12px 32px;
    background: #111; color: #eee;
    font-family: -apple-system, system-ui, "Segoe UI", Roboto, Arial, sans-serif;
  }
  h1 { font-size: 17px; margin: 0; letter-spacing: .5px; }
  header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
  #dot { width: 10px; height: 10px; border-radius: 50%; background: #666; flex: none; }
  #dot.ok { background: #00ff88; }
  #dot.err { background: #ff4444; }
  section {
    background: #1c1c1c; border: 1px solid #2e2e2e; border-radius: 12px;
    padding: 12px; margin-bottom: 12px;
  }
  .titulo { font-size: 11px; letter-spacing: 1.5px; color: #00d4ff; margin-bottom: 10px; }
  button {
    font: inherit; font-weight: 700; color: #fff; background: #333;
    border: 0; border-radius: 10px; padding: 14px 10px; cursor: pointer;
    touch-action: manipulation;
  }
  button:active { filter: brightness(1.5); }
  button:disabled { opacity: .35; }
  input {
    font: inherit; background: #000; color: #fff; border: 1px solid #444;
    border-radius: 8px; padding: 10px; text-align: center; width: 100%;
  }
  #reloj { font-size: 56px; font-weight: 800; text-align: center; letter-spacing: 2px; margin: 4px 0 12px; }
  #reloj.corriendo { color: #00ff88; }
  .fila { display: flex; gap: 8px; align-items: center; }
  .fila > * { flex: 1; }
  .equipo { background: #262626; border-radius: 10px; padding: 10px; margin-bottom: 8px; }
  .equipo .nombre { font-weight: 800; text-align: center; margin-bottom: 8px; word-break: break-word; }
  .puntos { font-size: 34px; font-weight: 800; text-align: center; color: #ffcc00; min-width: 64px; }
  .btn-p { font-size: 24px; max-width: 76px; }
  .faltas { display: flex; gap: 6px; justify-content: center; margin-top: 10px; align-items: center; }
  .punto { width: 16px; height: 16px; border-radius: 50%; background: #444; flex: none; }
  .punto.on { background: #ff2b2b; }
  .grid-fx { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .grid-fx button { min-height: 62px; font-size: 12px; }
  .verde { background: #1d7a4a; } .ambar { background: #8a6d1f; }
  .rojo  { background: #a32d2d; } .gris  { background: #3a3a3a; }
  #gate { position: fixed; inset: 0; background: #111; display: none; place-items: center; padding: 24px; }
  #gate.visible { display: grid; }
  #gate .caja { width: 100%; max-width: 300px; text-align: center; }
  #gate p { color: #aaa; font-size: 13px; line-height: 1.5; }
  #aviso { color: #ff6b6b; font-size: 13px; min-height: 18px; }
</style>
</head>
<body>

<header>
  <span id="dot"></span>
  <h1>MATCH IMPRO · CONTROL REMOTO</h1>
</header>

<section>
  <div class="titulo">CRONÓMETRO</div>
  <div id="reloj">--:--</div>
  <div class="fila" style="margin-bottom:8px">
    <input id="min" type="number" min="0" max="99" inputmode="numeric" placeholder="min">
    <input id="seg" type="number" min="0" max="59" inputmode="numeric" placeholder="seg">
    <button class="gris" onclick="fijarTiempo()">SET</button>
  </div>
  <div class="fila">
    <button class="verde" onclick="enviar({accion:'timer_start'})">▶ INICIO</button>
    <button class="ambar" onclick="enviar({accion:'timer_pause'})">⏸ PAUSA</button>
  </div>
</section>

<section>
  <div class="titulo">EQUIPOS</div>
  <div id="equipos"></div>
</section>

<section>
  <div class="titulo">EFECTOS DE SONIDO</div>
  <div class="grid-fx" id="fx"></div>
</section>

<div id="gate">
  <div class="caja">
    <div class="titulo">EMPAREJAR DISPOSITIVO</div>
    <p>Escribe el PIN que aparece en la pestaña <b>REMOTO</b> del panel de control.</p>
    <input id="pin-in" type="number" inputmode="numeric" placeholder="PIN" style="margin-bottom:10px">
    <button class="verde" style="width:100%" onclick="guardarPin()">ENTRAR</button>
    <p id="aviso"></p>
  </div>
</div>

<script>
var CLAVE = 'match_impro_pin';
var pin = localStorage.getItem(CLAVE) || '';
var ultimoEstado = null;
var enVuelo = false;

function gate(visible, mensaje) {
  document.getElementById('gate').classList.toggle('visible', visible);
  document.getElementById('aviso').textContent = mensaje || '';
}

function guardarPin() {
  pin = document.getElementById('pin-in').value.trim();
  localStorage.setItem(CLAVE, pin);
  gate(false);
  refrescar();
}

function marcar(estado) {
  document.getElementById('dot').className = estado;
}

function pedir(ruta, opciones) {
  opciones = opciones || {};
  opciones.headers = Object.assign({'X-Match-Pin': pin}, opciones.headers || {});
  opciones.cache = 'no-store';
  return fetch(ruta, opciones).then(function (r) {
    if (r.status === 401) { gate(true, pin ? 'PIN incorrecto.' : ''); throw new Error('pin'); }
    if (!r.ok) throw new Error('http ' + r.status);
    return r.json();
  });
}

function enviar(comando) {
  return pedir('/api/comando', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(comando)
  }).then(refrescar).catch(function () { marcar('err'); });
}

function fijarTiempo() {
  var m = parseInt(document.getElementById('min').value, 10) || 0;
  var s = parseInt(document.getElementById('seg').value, 10) || 0;
  enviar({accion: 'timer_set', segundos: m * 60 + s});
}

function mmss(total) {
  var m = Math.floor(total / 60), s = total % 60;
  return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
}

function pintar(estado) {
  var reloj = document.getElementById('reloj');
  reloj.textContent = mmss(estado.timer.restante);
  reloj.classList.toggle('corriendo', estado.timer.corriendo);

  var previo = ultimoEstado;
  var mismaEstructura = previo
    && previo.equipos.length === estado.equipos.length
    && previo.equipos.every(function (e, i) { return e.nombre === estado.equipos[i].nombre; });

  var cont = document.getElementById('equipos');
  if (!mismaEstructura) {
    cont.innerHTML = '';
    estado.equipos.forEach(function (eq, i) {
      var d = document.createElement('div');
      d.className = 'equipo';
      d.innerHTML =
        '<div class="nombre"></div>' +
        '<div class="fila">' +
          '<button class="btn-p gris" data-p="-1">−</button>' +
          '<div class="puntos"></div>' +
          '<button class="btn-p gris" data-p="1">+</button>' +
        '</div>' +
        '<div class="faltas"><i class="punto"></i><i class="punto"></i><i class="punto"></i></div>' +
        '<div class="fila" style="margin-top:8px">' +
          '<button class="gris" data-f="-1" style="font-size:12px">QUITAR FALTA</button>' +
          '<button class="rojo" data-f="1">FALTA</button>' +
        '</div>';
      d.querySelector('.nombre').textContent = eq.nombre;
      d.querySelectorAll('[data-p]').forEach(function (b) {
        b.onclick = function () { enviar({accion: 'puntos', equipo: i, delta: parseInt(b.dataset.p, 10)}); };
      });
      d.querySelectorAll('[data-f]').forEach(function (b) {
        b.onclick = function () { enviar({accion: 'faltas', equipo: i, delta: parseInt(b.dataset.f, 10)}); };
      });
      cont.appendChild(d);
    });
  }
  estado.equipos.forEach(function (eq, i) {
    var caja = cont.children[i];
    if (!caja) return;
    caja.querySelector('.puntos').textContent = eq.puntos;
    caja.querySelectorAll('.punto').forEach(function (p, k) {
      p.classList.toggle('on', k < eq.faltas);
    });
  });

  var fx = document.getElementById('fx');
  if (fx.children.length !== estado.sonidos.length) {
    fx.innerHTML = '';
    estado.sonidos.forEach(function (_, i) {
      var b = document.createElement('button');
      b.onclick = function () { enviar({accion: 'sonido', slot: i}); };
      fx.appendChild(b);
    });
  }
  estado.sonidos.forEach(function (snd, i) {
    var b = fx.children[i];
    b.textContent = snd.nombre;
    b.disabled = !snd.cargado;
  });

  ultimoEstado = estado;
}

function refrescar() {
  if (enVuelo) return Promise.resolve();
  enVuelo = true;
  return pedir('/api/estado')
    .then(function (estado) { marcar('ok'); pintar(estado); })
    .catch(function (e) { if (e.message !== 'pin') marcar('err'); })
    .then(function () { enVuelo = false; });
}

if (!pin) gate(true);
refrescar();
setInterval(function () { if (!document.hidden) refrescar(); }, 1000);
document.addEventListener('visibilitychange', function () { if (!document.hidden) refrescar(); });
</script>
</body>
</html>
"""


# ==============================================================================
# MANEJADOR HTTP
# ==============================================================================
class _ManejadorRemoto(BaseHTTPRequestHandler):
    """Atiende las peticiones del celular. Vive en el hilo del servidor."""

    protocol_version = "HTTP/1.1"
    server_version = "MatchImproDirector"
    sys_version = ""

    # --- utilidades de respuesta -------------------------------------------
    def _responder(self, codigo, cuerpo, tipo="application/json; charset=utf-8"):
        datos = cuerpo.encode("utf-8") if isinstance(cuerpo, str) else cuerpo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(datos)
        except (BrokenPipeError, ConnectionResetError):
            pass  # El celular cerró la pestaña a mitad de la respuesta.

    def _json(self, codigo, objeto):
        self._responder(codigo, json.dumps(objeto, ensure_ascii=False))

    def _pin_valido(self):
        enviado = self.headers.get("X-Match-Pin", "")
        if enviado and enviado == self.server.control.pin:
            return True
        time.sleep(PENALIZACION_PIN)
        return False

    # --- rutas --------------------------------------------------------------
    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta in ("/", "/index.html"):
            self._responder(200, PAGINA_HTML, "text/html; charset=utf-8")
        elif ruta == "/favicon.ico":
            # El navegador del celular lo pide solo; respondemos "sin contenido".
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif ruta == "/api/estado":
            if not self._pin_valido():
                self._json(401, {"error": "pin"})
                return
            self._json(200, self.server.control.leer_estado())
        else:
            self._json(404, {"error": "no encontrado"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/comando":
            self._json(404, {"error": "no encontrado"})
            return
        if not self._pin_valido():
            self._json(401, {"error": "pin"})
            return
        try:
            largo = int(self.headers.get("Content-Length", 0))
        except ValueError:
            largo = 0
        if largo <= 0 or largo > MAX_BODY:
            self._json(400, {"error": "cuerpo invalido"})
            return
        try:
            comando = json.loads(self.rfile.read(largo).decode("utf-8"))
            if not isinstance(comando, dict):
                raise ValueError
        except Exception:
            self._json(400, {"error": "json invalido"})
            return
        self.server.control.encolar(comando)
        self._json(200, {"ok": True})

    def log_message(self, formato, *args):
        pass  # Silencio: no ensuciamos la consola durante la función.


class _ServidorRemoto(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


# ==============================================================================
# FACHADA USADA POR LA APLICACIÓN
# ==============================================================================
class ControlRemoto:
    """
    Envuelve el servidor HTTP y hace de puente seguro con Tkinter.

    leer_estado : callable sin argumentos que devuelve un dict serializable.
                  Se invoca desde el hilo del servidor, así que debe limitarse
                  a leer datos simples (nunca widgets).
    """

    def __init__(self, leer_estado, puerto=8770, pin=None):
        self._leer_estado = leer_estado
        self.puerto = int(puerto)
        self.pin = pin or generar_pin()
        self.ip = obtener_ip_local()

        self._comandos = []
        self._lock = threading.Lock()
        self._servidor = None
        self._hilo = None

    # --- ciclo de vida ------------------------------------------------------
    @property
    def activo(self):
        return self._servidor is not None

    @property
    def url(self):
        return f"http://{self.ip}:{self.puerto}"

    def iniciar(self):
        """Levanta el servidor. Lanza OSError si el puerto está ocupado."""
        if self.activo:
            return
        self.ip = obtener_ip_local()
        servidor = _ServidorRemoto(("0.0.0.0", self.puerto), _ManejadorRemoto)
        servidor.control = self
        self._servidor = servidor
        self._hilo = threading.Thread(
            target=servidor.serve_forever,
            kwargs={"poll_interval": 0.2},
            daemon=True,
            name="MatchImproRemoto",
        )
        self._hilo.start()

    def detener(self):
        if not self.activo:
            return
        servidor, hilo = self._servidor, self._hilo
        self._servidor = None
        self._hilo = None
        threading.Thread(target=servidor.shutdown, daemon=True).start()
        if hilo:
            hilo.join(timeout=2)
        servidor.server_close()
        with self._lock:
            self._comandos.clear()

    # --- puente de datos ----------------------------------------------------
    def leer_estado(self):
        return self._leer_estado()

    def encolar(self, comando):
        with self._lock:
            # Tope defensivo: si la app estuviera trabada, no crecemos sin límite.
            if len(self._comandos) < 200:
                self._comandos.append(comando)

    def vaciar_comandos(self):
        """Devuelve y limpia los comandos pendientes (se llama desde Tkinter)."""
        with self._lock:
            pendientes, self._comandos = self._comandos, []
        return pendientes
