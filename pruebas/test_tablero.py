"""
Pruebas del motor de dibujo: caché de imágenes, rendimiento y contenido.
Necesitan una pantalla (real o virtual con xvfb-run).
"""

import os
import statistics
import sys
import tempfile
import time
import tkinter as tk
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from match_state import EstadoPartido  # noqa: E402
from tablero import CALIDAD_ALTA, CALIDAD_RAPIDA, CacheImagenes, Tablero  # noqa: E402


class BaseTablero(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.fondo = os.path.join(cls.dir.name, "fondo.png")
        cls.logo = os.path.join(cls.dir.name, "logo.png")
        cls.roto = os.path.join(cls.dir.name, "roto.png")
        Image.new("RGB", (1920, 1080), (20, 30, 60)).save(cls.fondo)
        Image.new("RGBA", (600, 400), (255, 200, 0, 255)).save(cls.logo)
        with open(cls.roto, "wb") as f:
            f.write(b"esto no es una imagen")

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.canvas = tk.Canvas(self.root, width=1280, height=720)
        self.canvas.pack()
        self.tablero = Tablero(self.canvas)
        self.estado = EstadoPartido(num_equipos=3)
        self.root.update()

    def tearDown(self):
        self.root.destroy()


class PruebasCache(BaseTablero):
    def test_la_imagen_se_escala_una_sola_vez(self):
        cache = CacheImagenes()
        primera = cache.escalada(self.fondo, 800, 600)
        segunda = cache.escalada(self.fondo, 800, 600)
        self.assertIsNotNone(primera)
        self.assertIs(primera, segunda)   # Mismo objeto: no se recalculó

    def test_otro_tamano_produce_otra_imagen(self):
        cache = CacheImagenes()
        a = cache.escalada(self.fondo, 800, 600)
        b = cache.escalada(self.fondo, 801, 600)
        self.assertIsNot(a, b)

    def test_alta_y_rapida_se_guardan_por_separado(self):
        cache = CacheImagenes()
        alta = cache.escalada(self.fondo, 400, 300, CALIDAD_ALTA)
        rapida = cache.escalada(self.fondo, 400, 300, CALIDAD_RAPIDA)
        self.assertIsNot(alta, rapida)

    def test_imagen_ilegible_se_marca_y_no_se_reintenta(self):
        cache = CacheImagenes()
        self.assertIsNone(cache.escalada(self.roto, 100, 100))
        self.assertTrue(cache.fallo(self.roto))
        # Segunda llamada: sigue devolviendo None sin volver a tocar el disco.
        self.assertIsNone(cache.escalada(self.roto, 100, 100))

    def test_archivo_inexistente_no_revienta(self):
        cache = CacheImagenes()
        self.assertIsNone(cache.escalada("/no/existe/nada.png", 100, 100))

    def test_olvidar_permite_recargar_el_mismo_archivo(self):
        cache = CacheImagenes()
        antes = cache.escalada(self.fondo, 200, 200)
        cache.olvidar(self.fondo)
        despues = cache.escalada(self.fondo, 200, 200)
        self.assertIsNot(antes, despues)

    def test_la_cache_no_crece_sin_limite(self):
        cache = CacheImagenes()
        for i in range(40):
            cache.escalada(self.fondo, 100 + i, 100)
        self.assertLessEqual(len(cache._escaladas), 8)

    def test_medidas_absurdas_devuelven_nada(self):
        cache = CacheImagenes()
        self.assertIsNone(cache.escalada(self.fondo, 0, 100))
        self.assertIsNone(cache.escalada("", 100, 100))


class PruebasDibujo(BaseTablero):
    def test_dibuja_todos_los_elementos(self):
        self.tablero.dibujar(self.estado, 1280, 720)
        self.assertGreater(len(self.canvas.find_all()), 10)

    def test_ventana_diminuta_no_dibuja_nada(self):
        self.tablero.dibujar(self.estado, 2, 2)
        self.assertEqual(len(self.canvas.find_all()), 0)

    def test_el_reloj_muestra_el_tiempo(self):
        self.estado.cronometro.fijar(125)
        self.tablero.dibujar(self.estado, 1280, 720)
        textos = [self.canvas.itemcget(i, "text") for i in self.canvas.find_all()
                  if self.canvas.type(i) == "text"]
        self.assertIn("02:05", textos)

    def test_los_puntos_aparecen_en_el_tablero(self):
        self.estado.sumar_puntos(0, 7)
        self.tablero.dibujar(self.estado, 1280, 720)
        textos = [self.canvas.itemcget(i, "text") for i in self.canvas.find_all()
                  if self.canvas.type(i) == "text"]
        self.assertIn("7", textos)

    def test_ocultar_el_timer_lo_quita(self):
        self.estado.diseno.ver_timer = False
        self.tablero.dibujar(self.estado, 1280, 720)
        textos = [self.canvas.itemcget(i, "text") for i in self.canvas.find_all()
                  if self.canvas.type(i) == "text"]
        self.assertNotIn("04:00", textos)

    def test_ocultar_faltas_reduce_los_circulos(self):
        self.tablero.dibujar(self.estado, 1280, 720)
        con = len([i for i in self.canvas.find_all() if self.canvas.type(i) == "oval"])
        self.estado.diseno.ver_faltas = False
        self.tablero.dibujar(self.estado, 1280, 720)
        sin = len([i for i in self.canvas.find_all() if self.canvas.type(i) == "oval"])
        self.assertEqual(con, 9)      # 3 equipos x 3 luces
        self.assertEqual(sin, 0)

    def test_el_outline_agrega_copias_del_texto(self):
        self.estado.diseno.ver_outline = False
        self.tablero.dibujar(self.estado, 1280, 720)
        sin = len(self.canvas.find_all())
        self.estado.diseno.ver_outline = True
        self.tablero.dibujar(self.estado, 1280, 720)
        con = len(self.canvas.find_all())
        self.assertEqual(con - sin, 8 * len(self.estado.equipos))

    def test_reloj_en_alerta_cambia_de_color(self):
        d = self.estado.diseno
        self.estado.cronometro.fijar(5)
        self.assertEqual(Tablero.color_timer(self.estado), d.color_alerta)
        self.estado.cronometro.fijar(200)
        self.assertEqual(Tablero.color_timer(self.estado), d.color_timer)

    def test_la_barra_de_color_usa_el_color_del_equipo(self):
        self.estado.pintar_equipo(0, "#123456")
        self.tablero.dibujar(self.estado, 1280, 720)
        rellenos = [self.canvas.itemcget(i, "fill") for i in self.canvas.find_all()]
        self.assertIn("#123456", rellenos)

    def test_sin_barra_de_color_no_aparece(self):
        self.estado.pintar_equipo(0, "#123456")
        self.estado.diseno.ver_barra_color = False
        self.tablero.dibujar(self.estado, 1280, 720)
        rellenos = [self.canvas.itemcget(i, "fill") for i in self.canvas.find_all()]
        self.assertNotIn("#123456", rellenos)

    def test_fondo_ilegible_no_impide_dibujar_el_marcador(self):
        self.estado.diseno.fondo_path = self.roto
        self.tablero.dibujar(self.estado, 1280, 720)
        self.assertGreater(len(self.canvas.find_all()), 10)

    def test_dibuja_con_fondo_y_logo(self):
        self.estado.diseno.fondo_path = self.fondo
        self.estado.diseno.logo_path = self.logo
        self.tablero.dibujar(self.estado, 1280, 720)
        imagenes = [i for i in self.canvas.find_all() if self.canvas.type(i) == "image"]
        self.assertEqual(len(imagenes), 2)

    def test_seis_equipos_caben(self):
        self.estado.ajustar_numero_equipos(6)
        self.tablero.dibujar(self.estado, 1920, 1080)
        ovalos = [i for i in self.canvas.find_all() if self.canvas.type(i) == "oval"]
        self.assertEqual(len(ovalos), 18)


class PruebasActualizacionIncremental(BaseTablero):
    def test_actualizar_timer_sin_dibujar_antes_pide_redibujado(self):
        self.assertFalse(self.tablero.actualizar_timer(self.estado))

    def test_actualizar_timer_no_recrea_los_elementos(self):
        self.tablero.dibujar(self.estado, 1280, 720)
        antes = self.canvas.find_all()
        self.estado.cronometro.fijar(90)
        self.assertTrue(self.tablero.actualizar_timer(self.estado))
        self.assertEqual(antes, self.canvas.find_all())   # Mismos ids: nada se recreó
        texto = self.canvas.itemcget(self.tablero._id_texto_timer, "text")
        self.assertEqual(texto, "01:30")

    def test_no_toca_el_canvas_si_el_segundo_no_cambio(self):
        self.tablero.dibujar(self.estado, 1280, 720)
        self.assertTrue(self.tablero.actualizar_timer(self.estado))
        self.assertTrue(self.tablero.actualizar_timer(self.estado))

    def test_el_color_de_alerta_se_aplica_al_actualizar(self):
        self.tablero.dibujar(self.estado, 1280, 720)
        self.estado.cronometro.fijar(3)
        self.tablero.actualizar_timer(self.estado)
        color = self.canvas.itemcget(self.tablero._id_texto_timer, "fill")
        self.assertEqual(color, self.estado.diseno.color_alerta)

    def test_sin_timer_visible_pide_redibujado(self):
        self.estado.diseno.ver_timer = False
        self.tablero.dibujar(self.estado, 1280, 720)
        self.assertFalse(self.tablero.actualizar_timer(self.estado))


class PruebasRendimiento(BaseTablero):
    """El tablero corre sobre el portátil del operador durante toda la función."""

    def medir(self, funcion, repeticiones=15):
        tiempos = []
        for _ in range(repeticiones):
            t0 = time.perf_counter()
            funcion()
            self.root.update_idletasks()
            tiempos.append((time.perf_counter() - t0) * 1000)
        return statistics.median(tiempos)

    def test_redibujado_con_fondo_full_hd_es_rapido(self):
        self.estado.diseno.fondo_path = self.fondo
        self.estado.diseno.logo_path = self.logo
        self.tablero.dibujar(self.estado, 1920, 1080)   # Primer dibujo: llena la caché
        mediana = self.medir(lambda: self.tablero.dibujar(self.estado, 1920, 1080))
        # La versión 1 tardaba ~64 ms de mediana en esta misma máquina.
        self.assertLess(mediana, 15, f"redibujado demasiado lento: {mediana:.1f} ms")

    def test_el_tic_del_reloj_es_casi_gratis(self):
        self.estado.diseno.fondo_path = self.fondo
        self.tablero.dibujar(self.estado, 1920, 1080)
        segundos = iter(range(200, 0, -1))

        def tic():
            self.estado.cronometro.fijar(next(segundos))
            self.tablero.actualizar_timer(self.estado)

        mediana = self.medir(tic, repeticiones=30)
        self.assertLess(mediana, 2, f"el tic del reloj cuesta {mediana:.2f} ms")


if __name__ == "__main__":
    unittest.main(verbosity=2)
