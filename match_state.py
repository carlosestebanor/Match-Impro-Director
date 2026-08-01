"""
MATCH DE IMPRO - DIRECTOR :: MODELO DE DATOS Y PERSISTENCIA
------------------------------------------------------------------------------
Aquí vive todo lo que el show "sabe": equipos, puntajes, faltas, cronómetro,
preferencias de diseño y guardado en disco. No depende de Tkinter ni de Pillow,
así que puede probarse sola y reutilizarse desde el mando a distancia.

Autor: Corporación Acción Impro
Ubicación: Medellín, Colombia
Año: 2026
Licencia: Creative Commons Atribución 4.0 Internacional (CC BY 4.0)
------------------------------------------------------------------------------
"""

import copy
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict

MAX_FALTAS = 3
MAX_EQUIPOS = 6
MIN_EQUIPOS = 2
NUM_SONIDOS = 6
TIEMPO_MAXIMO = 99 * 60 + 59      # 99:59, tope del cronómetro
PROFUNDIDAD_DESHACER = 60         # Cuántas jugadas se pueden revertir

# Nombres y colores típicos de un match de impro
EQUIPOS_POR_DEFECTO = [
    ("ROJO", "#e02020"),
    ("AMARILLO", "#f2c500"),
    ("AZUL", "#1f6feb"),
    ("VERDE", "#2ea043"),
    ("BLANCO", "#e6e6e6"),
    ("NEGRO", "#4a4a4a"),
]


# ==============================================================================
# EQUIPO
# ==============================================================================
@dataclass
class Equipo:
    nombre: str
    color: str = "#e02020"
    puntos: int = 0
    faltas: int = 0


# ==============================================================================
# DISEÑO DEL TABLERO (lo que el público ve)
# ==============================================================================
@dataclass
class Diseno:
    """Preferencias visuales de la proyección."""
    # Escalas y posiciones (fracciones del alto/ancho de la ventana)
    scale_factor: float = 1.0
    name_scale: float = 1.0
    offset_global_y: float = 0.0
    offset_names: float = 0.0
    offset_scores: float = 0.0
    offset_timer: float = 0.0
    offset_x: float = 0.0

    # Logo
    logo_scale: float = 0.5
    logo_offset_y: float = -0.4

    # Tipografías
    font_family: str = "Arial"
    font_score: str = "Impact"

    # Colores
    color_nombres: str = "#ffffff"
    color_puntos: str = "#ffcc00"
    color_faltas: str = "#ff0000"
    color_caja: str = "#000000"
    color_timer: str = "#ffffff"
    color_alerta: str = "#ff3b30"     # Cronómetro en los segundos finales

    # Cajas
    box_padding: float = 1.0
    corner_radius: int = 20

    # Ubicación y visibilidad
    timer_position: str = "Abajo"
    ver_timer: bool = True
    ver_faltas: bool = True
    ver_outline: bool = True
    ver_barra_color: bool = True      # Franja con el color de cada equipo
    segundos_alerta: int = 10         # Desde cuándo el reloj se pone en alerta

    # Rutas de imágenes
    fondo_path: str = ""
    logo_path: str = ""

    def a_dict(self):
        return asdict(self)

    def aplicar_dict(self, datos):
        """Carga solo las claves conocidas, ignorando basura o versiones viejas."""
        for clave, valor in (datos or {}).items():
            if hasattr(self, clave):
                actual = getattr(self, clave)
                try:
                    if isinstance(actual, bool):
                        setattr(self, clave, bool(valor))
                    elif isinstance(actual, int) and not isinstance(actual, bool):
                        setattr(self, clave, int(valor))
                    elif isinstance(actual, float):
                        setattr(self, clave, float(valor))
                    elif isinstance(actual, str):
                        setattr(self, clave, str(valor))
                except (TypeError, ValueError):
                    pass  # Valor corrupto: nos quedamos con el que ya teníamos.


# ==============================================================================
# SONIDOS
# ==============================================================================
@dataclass
class RanuraSonido:
    nombre: str
    path: str = ""
    # 'obj' guarda el pygame.mixer.Sound; no se serializa.
    obj: object = field(default=None, repr=False, compare=False)

    @property
    def cargado(self):
        return self.obj is not None

    @property
    def archivo_existe(self):
        return bool(self.path) and os.path.isfile(self.path)


# ==============================================================================
# CRONÓMETRO
# ==============================================================================
class Cronometro:
    """
    Cuenta regresiva basada en reloj monotónico.

    La versión anterior restaba 1 a un contador cada `after(1000)`, así que
    acumulaba el retraso de cada redibujado: en un match largo el reloj del
    tablero se separaba varios segundos del real. Aquí el tiempo se calcula
    siempre contra el reloj del sistema, por lo que no existe deriva.
    """

    def __init__(self, duracion=240, fuente_tiempo=time.monotonic):
        self._ahora = fuente_tiempo
        self.duracion = int(duracion)   # Último valor fijado con SET
        self._restante = float(duracion)
        self._fin = None                # Instante monotónico en que llegaría a 0

    # --- consulta ---
    @property
    def corriendo(self):
        return self._fin is not None

    @property
    def restante(self):
        """Segundos restantes, redondeados hacia arriba (como un reloj de pared)."""
        if self._fin is None:
            crudo = self._restante
        else:
            crudo = self._fin - self._ahora()
        if crudo <= 0:
            return 0
        # Techo: mostramos 04:00 durante el primer segundo, no 03:59.
        return min(TIEMPO_MAXIMO, int(crudo) + (1 if crudo % 1 else 0))

    @property
    def agotado(self):
        return self.restante == 0

    def texto(self):
        seg = self.restante
        return f"{seg // 60:02d}:{seg % 60:02d}"

    # --- control ---
    def fijar(self, segundos):
        """Deja el reloj en un valor concreto, conservando si estaba corriendo."""
        segundos = max(0, min(int(segundos), TIEMPO_MAXIMO))
        self.duracion = segundos
        if self.corriendo:
            self._fin = self._ahora() + segundos
        else:
            self._restante = float(segundos)
        return segundos

    def ajustar(self, delta):
        """Suma o resta segundos en caliente (botones ±30 s)."""
        return self.fijar(self.restante + int(delta))

    def iniciar(self):
        if self.corriendo or self.restante <= 0:
            return False
        self._fin = self._ahora() + self._restante
        return True

    def pausar(self):
        if not self.corriendo:
            return False
        self._restante = max(0.0, self._fin - self._ahora())
        self._fin = None
        return True

    def alternar(self):
        return self.pausar() if self.corriendo else self.iniciar()

    def reiniciar(self):
        """Vuelve al último tiempo fijado con SET y detiene la cuenta."""
        self._fin = None
        self._restante = float(self.duracion)

    def revisar_agotado(self):
        """Congela el reloj en 0 al terminar. Devuelve True solo la primera vez."""
        if self.corriendo and self._fin - self._ahora() <= 0:
            self._fin = None
            self._restante = 0.0
            return True
        return False


# ==============================================================================
# ESTADO COMPLETO DEL PARTIDO
# ==============================================================================
class EstadoPartido:
    """Equipos + cronómetro + sonidos + diseño, con deshacer/rehacer."""

    def __init__(self, num_equipos=3, fuente_tiempo=time.monotonic):
        self.equipos = []
        self.diseno = Diseno()
        self.cronometro = Cronometro(240, fuente_tiempo=fuente_tiempo)
        self.sonidos = [RanuraSonido(nombre=f"FX {i + 1}") for i in range(NUM_SONIDOS)]
        self.volumen = 0.8
        self._retirados = []      # Equipos quitados con el selector de cantidad
        self.ajustar_numero_equipos(num_equipos)
        self._pila_deshacer = []
        self._pila_rehacer = []

    # --- estructura de equipos ---------------------------------------------
    def ajustar_numero_equipos(self, n):
        """
        Crece o recorta la lista de equipos conservando los datos existentes.

        Los equipos que se quitan no se destruyen: quedan apartados y vuelven
        con su nombre, color y marcador si el operador sube otra vez la cifra.
        Bajar el selector por error ya no borra los nombres escritos a mano.
        """
        n = max(MIN_EQUIPOS, min(int(n), MAX_EQUIPOS))
        while len(self.equipos) < n:
            if self._retirados:
                self.equipos.append(self._retirados.pop(0))
                continue
            i = len(self.equipos)
            nombre, color = EQUIPOS_POR_DEFECTO[i % len(EQUIPOS_POR_DEFECTO)]
            self.equipos.append(Equipo(nombre=nombre, color=color))
        if len(self.equipos) > n:
            self._retirados = self.equipos[n:] + self._retirados
            del self._retirados[MAX_EQUIPOS:]
            del self.equipos[n:]
        return len(self.equipos)

    def indice_valido(self, idx):
        return isinstance(idx, int) and 0 <= idx < len(self.equipos)

    # --- deshacer / rehacer -------------------------------------------------
    def _fotografiar(self):
        """Guarda el marcador antes de modificarlo."""
        self._pila_deshacer.append([(e.puntos, e.faltas) for e in self.equipos])
        if len(self._pila_deshacer) > PROFUNDIDAD_DESHACER:
            self._pila_deshacer.pop(0)
        self._pila_rehacer.clear()

    def _restaurar(self, foto):
        for equipo, (puntos, faltas) in zip(self.equipos, foto):
            equipo.puntos, equipo.faltas = puntos, faltas

    @property
    def puede_deshacer(self):
        return bool(self._pila_deshacer)

    @property
    def puede_rehacer(self):
        return bool(self._pila_rehacer)

    def deshacer(self):
        if not self._pila_deshacer:
            return False
        self._pila_rehacer.append([(e.puntos, e.faltas) for e in self.equipos])
        self._restaurar(self._pila_deshacer.pop())
        return True

    def rehacer(self):
        if not self._pila_rehacer:
            return False
        self._pila_deshacer.append([(e.puntos, e.faltas) for e in self.equipos])
        self._restaurar(self._pila_rehacer.pop())
        return True

    # --- marcador -----------------------------------------------------------
    def sumar_puntos(self, idx, delta):
        if not self.indice_valido(idx):
            return False
        equipo = self.equipos[idx]
        nuevo = equipo.puntos + int(delta)
        if nuevo < 0 or nuevo > 999:
            return False
        self._fotografiar()
        equipo.puntos = nuevo
        return True

    def sumar_faltas(self, idx, delta):
        if not self.indice_valido(idx):
            return False
        equipo = self.equipos[idx]
        nuevo = equipo.faltas + int(delta)
        if not (0 <= nuevo <= MAX_FALTAS):
            return False
        self._fotografiar()
        equipo.faltas = nuevo
        return True

    def renombrar(self, idx, nombre):
        if not self.indice_valido(idx):
            return False
        self.equipos[idx].nombre = str(nombre)[:40]
        return True

    def pintar_equipo(self, idx, color):
        if not self.indice_valido(idx):
            return False
        self.equipos[idx].color = str(color)
        return True

    def reiniciar_marcador(self):
        """Deja puntos y faltas en cero (los nombres se conservan)."""
        self._fotografiar()
        for equipo in self.equipos:
            equipo.puntos = 0
            equipo.faltas = 0
        self.cronometro.reiniciar()

    # --- foto para el mando a distancia -------------------------------------
    def resumen(self):
        # Lo llama el hilo del servidor remoto mientras el hilo de la interfaz
        # puede estar cambiando el número de equipos: tomamos una referencia
        # estable de cada lista antes de recorrerla.
        equipos = list(self.equipos)
        sonidos = list(self.sonidos)
        return {
            'equipos': [{'nombre': e.nombre, 'puntos': e.puntos,
                         'faltas': e.faltas, 'color': e.color} for e in equipos],
            'timer': {'restante': self.cronometro.restante,
                      'corriendo': self.cronometro.corriendo},
            'sonidos': [{'nombre': s.nombre, 'cargado': s.cargado} for s in sonidos],
            'max_faltas': MAX_FALTAS,
            'puede_deshacer': self.puede_deshacer,
        }

    # --- serialización ------------------------------------------------------
    def a_dict(self):
        return {
            'version': 2,
            'equipos': [{'nombre': e.nombre, 'color': e.color,
                         'puntos': e.puntos, 'faltas': e.faltas} for e in self.equipos],
            'diseno': self.diseno.a_dict(),
            'sonidos': [{'nombre': s.nombre, 'path': s.path} for s in self.sonidos],
            'volumen': self.volumen,
            'duracion_timer': self.cronometro.duracion,
        }

    def aplicar_dict(self, datos, incluir_marcador=True):
        """Carga una configuración guardada. Tolera archivos incompletos."""
        if not isinstance(datos, dict):
            raise ValueError("El archivo no contiene una configuración válida.")

        equipos = datos.get('equipos')
        if isinstance(equipos, list) and equipos:
            # El preset manda: los equipos apartados de la sesión anterior no
            # deben reaparecer encima de los que trae el archivo.
            self._retirados.clear()
            self.ajustar_numero_equipos(len(equipos))
            for equipo, guardado in zip(self.equipos, equipos):
                if not isinstance(guardado, dict):
                    continue
                equipo.nombre = str(guardado.get('nombre', equipo.nombre))[:40]
                equipo.color = str(guardado.get('color', equipo.color))
                if incluir_marcador:
                    try:
                        equipo.puntos = max(0, min(int(guardado.get('puntos', 0)), 999))
                        equipo.faltas = max(0, min(int(guardado.get('faltas', 0)), MAX_FALTAS))
                    except (TypeError, ValueError):
                        equipo.puntos, equipo.faltas = 0, 0

        self.diseno.aplicar_dict(datos.get('diseno'))

        sonidos = datos.get('sonidos')
        if isinstance(sonidos, list):
            for ranura, guardado in zip(self.sonidos, sonidos):
                if isinstance(guardado, dict):
                    ranura.nombre = str(guardado.get('nombre', ranura.nombre))[:24]
                    ranura.path = str(guardado.get('path', "") or "")

        try:
            self.volumen = max(0.0, min(float(datos.get('volumen', self.volumen)), 1.0))
        except (TypeError, ValueError):
            pass

        try:
            self.cronometro.fijar(int(datos.get('duracion_timer', self.cronometro.duracion)))
        except (TypeError, ValueError):
            pass

        self._pila_deshacer.clear()
        self._pila_rehacer.clear()

    def copia_profunda(self):
        return copy.deepcopy(self.a_dict())


# ==============================================================================
# GUARDADO EN DISCO
# ==============================================================================
NOMBRE_CONFIG = "match_director_config.json"


def carpeta_app():
    """Carpeta del ejecutable (o del script) — así los presets viajan en el USB."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def carpeta_usuario():
    return os.path.join(os.path.expanduser("~"), ".match_impro_director")


def ruta_config():
    """
    Preferimos guardar junto al programa (portátil). Si esa carpeta es de solo
    lectura —típico si lo instalaron en 'Archivos de programa'— usamos la
    carpeta personal del usuario.
    """
    # Escotilla para las pruebas automáticas (y para quien quiera fijar la ruta).
    forzada = os.environ.get("MATCH_DIRECTOR_CONFIG")
    if forzada:
        return forzada

    destino = carpeta_app()
    if os.access(destino, os.W_OK):
        return os.path.join(destino, NOMBRE_CONFIG)
    alterno = carpeta_usuario()
    os.makedirs(alterno, exist_ok=True)
    return os.path.join(alterno, NOMBRE_CONFIG)


def guardar_json(datos, ruta):
    """
    Escritura segura: primero un archivo temporal y luego el reemplazo atómico.
    Si se corta la luz a mitad del guardado, la configuración anterior sobrevive.
    """
    carpeta = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(carpeta, exist_ok=True)
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal, ruta)
    return ruta


def cargar_json(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)
