"""
MATCH DE IMPRO - DIRECTOR :: MOTOR DE RENDERIZADO DEL TABLERO
------------------------------------------------------------------------------
Dibuja lo que ve el público. Está separado del panel de control para poder
optimizarlo sin tocar la interfaz del operador.

Optimizaciones frente a la versión 1:
  · Caché de imágenes: el fondo y el logo se reescalan solo cuando cambia el
    tamaño de la ventana, no en cada redibujado. Antes, con un fondo Full HD,
    cada segundo de cronómetro costaba ~78 ms de CPU.
  · Reescalado en dos tiempos: durante el arrastre de la ventana se usa un
    filtro rápido y, al soltar, se refina con LANCZOS.
  · Actualización incremental: si solo cambió el reloj, se reescribe ese texto
    en lugar de reconstruir el tablero completo.
  · Las imágenes que no se pueden abrir se marcan y no se reintentan en bucle.

Autor: Corporación Acción Impro
Ubicación: Medellín, Colombia
Año: 2026
Licencia: Creative Commons Atribución 4.0 Internacional (CC BY 4.0)
------------------------------------------------------------------------------
"""

from PIL import Image, ImageTk

from match_state import MAX_FALTAS

CALIDAD_ALTA = "alta"
CALIDAD_RAPIDA = "rapida"

_FILTROS = {
    CALIDAD_ALTA: Image.Resampling.LANCZOS,
    CALIDAD_RAPIDA: Image.Resampling.BILINEAR,
}

# Tope de imágenes escaladas en memoria (fondo + logo, alta y rápida, con holgura)
MAX_ENTRADAS_CACHE = 8


class CacheImagenes:
    """Guarda las imágenes ya abiertas y ya escaladas para no repetir trabajo."""

    def __init__(self):
        self._originales = {}   # ruta -> PIL.Image
        self._escaladas = {}    # (ruta, ancho, alto, calidad) -> ImageTk.PhotoImage
        self._fallidas = set()  # rutas que no se pudieron abrir

    def _original(self, ruta):
        if ruta in self._fallidas:
            return None
        img = self._originales.get(ruta)
        if img is None:
            try:
                img = Image.open(ruta)
                img.load()                     # Fuerza la lectura ya, no en el primer dibujo
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                self._originales[ruta] = img
            except Exception:
                self._fallidas.add(ruta)
                return None
        return img

    def escalada(self, ruta, ancho, alto, calidad=CALIDAD_ALTA):
        """Devuelve la imagen lista para el canvas, reutilizando la caché."""
        if not ruta or ancho < 1 or alto < 1:
            return None
        clave = (ruta, int(ancho), int(alto), calidad)
        cacheada = self._escaladas.get(clave)
        if cacheada is not None:
            return cacheada

        original = self._original(ruta)
        if original is None:
            return None
        try:
            redimensionada = original.resize((int(ancho), int(alto)), _FILTROS[calidad])
            foto = ImageTk.PhotoImage(redimensionada)
        except Exception:
            self._fallidas.add(ruta)
            return None

        if len(self._escaladas) >= MAX_ENTRADAS_CACHE:
            # Caché diminuta: al llenarse la vaciamos entera, es más barato que
            # llevar contabilidad de accesos.
            self._escaladas.clear()
        self._escaladas[clave] = foto
        return foto

    def olvidar(self, ruta=None):
        """Invalida una ruta concreta (o todo) tras cambiar de archivo."""
        if ruta is None:
            self._originales.clear()
            self._escaladas.clear()
            self._fallidas.clear()
            return
        self._originales.pop(ruta, None)
        self._fallidas.discard(ruta)
        self._escaladas = {k: v for k, v in self._escaladas.items() if k[0] != ruta}

    def fallo(self, ruta):
        return ruta in self._fallidas


class Tablero:
    """Pinta el marcador sobre un tk.Canvas."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.cache = CacheImagenes()
        self._id_texto_timer = None
        self._ultimo_texto_timer = None
        self._ultimo_color_timer = None
        # Referencias vivas a las PhotoImage: si se recolectan, el canvas queda en blanco.
        self._ref_fondo = None
        self._ref_logo = None

    # --- utilidades de dibujo ----------------------------------------------
    def _caja_redondeada(self, x1, y1, x2, y2, radio, **kwargs):
        """Rectángulo de esquinas suaves (polígono con puntos duplicados)."""
        radio = max(0, min(radio, abs(x2 - x1) / 2, abs(y2 - y1) / 2))
        puntos = [
            x1 + radio, y1, x1 + radio, y1, x2 - radio, y1, x2 - radio, y1,
            x2, y1, x2, y1 + radio, x2, y1 + radio, x2, y2 - radio,
            x2, y2 - radio, x2, y2, x2 - radio, y2, x2 - radio, y2,
            x1 + radio, y2, x1 + radio, y2, x1, y2, x1, y2 - radio,
            x1, y2 - radio, x1, y1 + radio, x1, y1 + radio, x1, y1,
        ]
        return self.canvas.create_polygon(puntos, smooth=True, **kwargs)

    def _texto_con_borde(self, x, y, texto, fuente, color, ancho_max, con_borde, grosor):
        """Texto centrado, con contorno negro opcional para que resalte sobre el fondo."""
        if con_borde and grosor > 0:
            for dx in (-grosor, 0, grosor):
                for dy in (-grosor, 0, grosor):
                    if dx or dy:
                        self.canvas.create_text(x + dx, y + dy, text=texto, font=fuente,
                                                fill="black", width=ancho_max, justify="center")
        return self.canvas.create_text(x, y, text=texto, font=fuente, fill=color,
                                       width=ancho_max, justify="center")

    # --- color del cronómetro ----------------------------------------------
    @staticmethod
    def color_timer(estado):
        """Blanco normalmente; color de alerta en los segundos finales."""
        d = estado.diseno
        restante = estado.cronometro.restante
        if restante <= d.segundos_alerta:
            return d.color_alerta
        return d.color_timer

    # --- actualización barata ----------------------------------------------
    def actualizar_timer(self, estado):
        """
        Reescribe solo el reloj. Devuelve False si hace falta un redibujado
        completo (por ejemplo, si el tablero aún no se ha dibujado).
        """
        if self._id_texto_timer is None:
            return False
        texto = estado.cronometro.texto()
        color = self.color_timer(estado)
        if texto == self._ultimo_texto_timer and color == self._ultimo_color_timer:
            return True  # Nada que hacer: mismo segundo en pantalla.
        try:
            self.canvas.itemconfigure(self._id_texto_timer, text=texto, fill=color)
        except Exception:
            return False
        self._ultimo_texto_timer = texto
        self._ultimo_color_timer = color
        return True

    # --- dibujado completo --------------------------------------------------
    def dibujar(self, estado, ancho, alto, calidad=CALIDAD_ALTA):
        """Reconstruye el tablero entero."""
        canvas = self.canvas
        canvas.delete("all")
        self._id_texto_timer = None
        self._ultimo_texto_timer = None
        self._ultimo_color_timer = None

        if ancho < 10 or alto < 10:
            return  # Ventana todavía sin tamaño real.

        d = estado.diseno

        # 1. Fondo -----------------------------------------------------------
        if d.fondo_path:
            fondo = self.cache.escalada(d.fondo_path, ancho, alto, calidad)
            if fondo is not None:
                self._ref_fondo = fondo
                canvas.create_image(0, 0, image=fondo, anchor="nw")

        # 2. Logo ------------------------------------------------------------
        if d.logo_path:
            original = self.cache._original(d.logo_path)
            if original is not None and original.height:
                alto_logo = max(1, int(alto * 0.2 * d.logo_scale))
                ancho_logo = max(1, int(alto_logo * (original.width / original.height)))
                logo = self.cache.escalada(d.logo_path, ancho_logo, alto_logo, calidad)
                if logo is not None:
                    self._ref_logo = logo
                    canvas.create_image(ancho * 0.5, (alto * 0.5) + (alto * d.logo_offset_y),
                                        image=logo, anchor="center")

        # 3. Medidas base ----------------------------------------------------
        fuente_base = max(8, int(alto * 0.05 * d.scale_factor))
        grosor_borde = max(2, int(fuente_base * 0.06))
        cx = ancho * 0.5 + (ancho * d.offset_x)

        cy_equipos = (alto * 0.5) + (alto * d.offset_global_y)
        cy_timer = (alto * 0.15) if d.timer_position == "Arriba" else (alto * 0.85)
        cy_timer += (alto * d.offset_timer)

        # 4. Cronómetro ------------------------------------------------------
        if d.ver_timer:
            t_w = ancho * 0.25 * d.scale_factor * d.box_padding
            t_h = alto * 0.15 * d.scale_factor * d.box_padding
            self._caja_redondeada(cx - t_w / 2, cy_timer - t_h / 2,
                                  cx + t_w / 2, cy_timer + t_h / 2,
                                  radio=d.corner_radius, fill=d.color_caja)
            texto = estado.cronometro.texto()
            color = self.color_timer(estado)
            self._id_texto_timer = canvas.create_text(
                cx, cy_timer, text=texto, fill=color,
                font=(d.font_score, int(fuente_base * 2.5)))
            self._ultimo_texto_timer = texto
            self._ultimo_color_timer = color

        # 5. Equipos ---------------------------------------------------------
        equipos = estado.equipos
        if not equipos:
            return
        col_w = ancho / len(equipos)

        for i, equipo in enumerate(equipos):
            x = (i * col_w) + (col_w / 2) + (ancho * d.offset_x)
            y_nombre = cy_equipos - (alto * 0.12) + (alto * d.offset_names)
            y_puntos = cy_equipos + (alto * 0.02) + (alto * d.offset_scores)

            # Nombre
            id_nombre = self._texto_con_borde(
                x, y_nombre, equipo.nombre,
                (d.font_family, int(fuente_base * d.name_scale), "bold"),
                d.color_nombres, col_w * 0.9, d.ver_outline, grosor_borde)

            # Franja con el color del equipo (ayuda a identificarlo desde lejos).
            # Se coloca sobre la caja real del texto: así no choca con los
            # nombres que ocupan dos o tres líneas.
            if d.ver_barra_color:
                barra_w = col_w * 0.42 * d.scale_factor
                barra_h = max(3.0, alto * 0.012 * d.scale_factor)
                caja = canvas.bbox(id_nombre)
                tope = caja[1] if caja else y_nombre - fuente_base * d.name_scale
                y_barra = tope - barra_h - max(2.0, alto * 0.012)
                self._caja_redondeada(x - barra_w / 2, y_barra,
                                      x + barra_w / 2, y_barra + barra_h,
                                      radio=barra_h / 2, fill=equipo.color, outline="")

            # Puntos
            p_w = alto * 0.2 * d.scale_factor * d.box_padding
            p_h = p_w * 0.8
            self._caja_redondeada(x - p_w / 2, y_puntos - p_h / 2,
                                  x + p_w / 2, y_puntos + p_h / 2,
                                  radio=d.corner_radius, fill=d.color_caja)
            canvas.create_text(x, y_puntos, text=str(equipo.puntos), fill=d.color_puntos,
                               font=(d.font_score, int(fuente_base * 3)))

            # Faltas (semáforo de 3 luces)
            if d.ver_faltas:
                y_faltas = y_puntos + (alto * 0.16)
                f_w, f_h = p_w, p_h * 0.4
                self._caja_redondeada(x - f_w / 2, y_faltas - f_h / 2,
                                      x + f_w / 2, y_faltas + f_h / 2,
                                      radio=d.corner_radius, fill=d.color_caja)
                r = f_h * 0.3
                hueco = r * 0.5
                inicio = x - ((r * 2 * MAX_FALTAS + hueco * (MAX_FALTAS - 1)) / 2) + r
                for k in range(MAX_FALTAS):
                    px = inicio + k * (r * 2 + hueco)
                    color = d.color_faltas if k < equipo.faltas else "#333333"
                    canvas.create_oval(px - r, y_faltas - r, px + r, y_faltas + r,
                                       fill=color, outline="")
