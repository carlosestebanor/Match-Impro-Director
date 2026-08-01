"""
Pruebas del modelo de datos: equipos, cronómetro, deshacer y guardado.
No necesitan pantalla ni audio.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from match_state import (  # noqa: E402
    MAX_EQUIPOS, MAX_FALTAS, MIN_EQUIPOS, TIEMPO_MAXIMO,
    Cronometro, Diseno, EstadoPartido, cargar_json, guardar_json,
)


class RelojFalso:
    """Reloj controlado a mano para probar el cronómetro sin esperar."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avanzar(self, segundos):
        self.t += segundos


class PruebasCronometro(unittest.TestCase):
    def setUp(self):
        self.reloj = RelojFalso()
        self.crono = Cronometro(240, fuente_tiempo=self.reloj)

    def test_arranca_detenido_en_el_valor_dado(self):
        self.assertFalse(self.crono.corriendo)
        self.assertEqual(self.crono.restante, 240)
        self.assertEqual(self.crono.texto(), "04:00")

    def test_muestra_el_valor_completo_durante_el_primer_segundo(self):
        # Un reloj de pared muestra 04:00 hasta que pasa el primer segundo.
        self.crono.iniciar()
        self.reloj.avanzar(0.3)
        self.assertEqual(self.crono.texto(), "04:00")
        self.reloj.avanzar(0.8)
        self.assertEqual(self.crono.texto(), "03:59")

    def test_no_acumula_deriva(self):
        """El fallo de la versión 1: restar 1 por tick perdía segundos reales."""
        self.crono.iniciar()
        for _ in range(100):
            self.reloj.avanzar(1.017)   # Cada tick llega tarde, como en la vida real
        # Han pasado 101.7 s reales, así que quedan 138.3 -> se muestra 02:19.
        self.assertEqual(self.crono.restante, 139)
        self.assertEqual(self.crono.texto(), "02:19")
        # La versión 1 habría restado un segundo por tick y mostraría 02:20.
        self.assertNotEqual(self.crono.restante, 140)

    def test_pausa_congela_y_reanuda(self):
        self.crono.iniciar()
        self.reloj.avanzar(40)
        self.assertTrue(self.crono.pausar())
        self.assertEqual(self.crono.restante, 200)
        self.reloj.avanzar(300)                    # Tiempo muerto entre escenas
        self.assertEqual(self.crono.restante, 200)
        self.crono.iniciar()
        self.reloj.avanzar(10)
        self.assertEqual(self.crono.restante, 190)

    def test_pausar_dos_veces_no_hace_nada(self):
        self.crono.iniciar()
        self.assertTrue(self.crono.pausar())
        self.assertFalse(self.crono.pausar())

    def test_no_baja_de_cero(self):
        self.crono.fijar(3)
        self.crono.iniciar()
        self.reloj.avanzar(60)
        self.assertEqual(self.crono.restante, 0)
        self.assertTrue(self.crono.agotado)

    def test_revisar_agotado_avisa_una_sola_vez(self):
        self.crono.fijar(2)
        self.crono.iniciar()
        self.reloj.avanzar(5)
        self.assertTrue(self.crono.revisar_agotado())
        self.assertFalse(self.crono.revisar_agotado())
        self.assertFalse(self.crono.corriendo)

    def test_no_inicia_en_cero(self):
        self.crono.fijar(0)
        self.assertFalse(self.crono.iniciar())

    def test_fijar_mientras_corre_mantiene_la_marcha(self):
        self.crono.iniciar()
        self.reloj.avanzar(10)
        self.crono.fijar(60)
        self.assertTrue(self.crono.corriendo)
        self.assertEqual(self.crono.restante, 60)
        self.reloj.avanzar(20)
        self.assertEqual(self.crono.restante, 40)

    def test_ajustar_suma_y_resta_sin_pasarse(self):
        self.crono.fijar(100)
        self.assertEqual(self.crono.ajustar(30), 130)
        self.assertEqual(self.crono.ajustar(-500), 0)

    def test_tope_maximo(self):
        self.assertEqual(self.crono.fijar(10 ** 9), TIEMPO_MAXIMO)

    def test_reiniciar_vuelve_al_ultimo_set(self):
        self.crono.fijar(180)
        self.crono.iniciar()
        self.reloj.avanzar(60)
        self.crono.reiniciar()
        self.assertFalse(self.crono.corriendo)
        self.assertEqual(self.crono.restante, 180)


class PruebasEquipos(unittest.TestCase):
    def setUp(self):
        self.estado = EstadoPartido(num_equipos=3)

    def test_equipos_por_defecto(self):
        self.assertEqual([e.nombre for e in self.estado.equipos],
                         ["ROJO", "AMARILLO", "AZUL"])
        self.assertTrue(all(e.color.startswith("#") for e in self.estado.equipos))

    def test_crecer_conserva_los_existentes(self):
        self.estado.renombrar(0, "LOS PERROS")
        self.estado.sumar_puntos(0, 5)
        self.estado.ajustar_numero_equipos(5)
        self.assertEqual(len(self.estado.equipos), 5)
        self.assertEqual(self.estado.equipos[0].nombre, "LOS PERROS")
        self.assertEqual(self.estado.equipos[0].puntos, 5)

    def test_limites_de_cantidad(self):
        self.assertEqual(self.estado.ajustar_numero_equipos(99), MAX_EQUIPOS)
        self.assertEqual(self.estado.ajustar_numero_equipos(0), MIN_EQUIPOS)

    def test_bajar_y_subir_la_cifra_no_borra_los_nombres(self):
        """Bajar el selector por error no debe costar los nombres escritos."""
        self.estado.renombrar(2, "IMPROVISTOS")
        self.estado.pintar_equipo(2, "#ff0055")
        self.estado.sumar_puntos(2, 8)
        self.estado.ajustar_numero_equipos(2)     # Se cae el tercer equipo
        self.estado.ajustar_numero_equipos(3)     # Y vuelve
        self.assertEqual(self.estado.equipos[2].nombre, "IMPROVISTOS")
        self.assertEqual(self.estado.equipos[2].color, "#ff0055")
        self.assertEqual(self.estado.equipos[2].puntos, 8)

    def test_los_equipos_vuelven_en_su_orden(self):
        for i, nombre in enumerate(["A", "B", "C"]):
            self.estado.renombrar(i, nombre)
        self.estado.ajustar_numero_equipos(4)
        self.estado.renombrar(3, "D")
        self.estado.ajustar_numero_equipos(2)
        self.estado.ajustar_numero_equipos(4)
        self.assertEqual([e.nombre for e in self.estado.equipos], ["A", "B", "C", "D"])

    def test_un_preset_manda_sobre_los_equipos_apartados(self):
        self.estado.renombrar(2, "VIEJO")
        self.estado.ajustar_numero_equipos(2)
        self.estado.aplicar_dict({"equipos": [{"nombre": "X"}, {"nombre": "Y"},
                                              {"nombre": "Z"}]})
        self.assertEqual([e.nombre for e in self.estado.equipos], ["X", "Y", "Z"])

    def test_los_apartados_no_crecen_sin_limite(self):
        for _ in range(30):
            self.estado.ajustar_numero_equipos(MAX_EQUIPOS)
            self.estado.ajustar_numero_equipos(MIN_EQUIPOS)
        self.assertLessEqual(len(self.estado._retirados), MAX_EQUIPOS)

    def test_puntos_no_bajan_de_cero(self):
        self.assertFalse(self.estado.sumar_puntos(0, -1))
        self.assertEqual(self.estado.equipos[0].puntos, 0)

    def test_faltas_topan_en_el_maximo(self):
        for _ in range(MAX_FALTAS):
            self.assertTrue(self.estado.sumar_faltas(1, 1))
        self.assertFalse(self.estado.sumar_faltas(1, 1))
        self.assertEqual(self.estado.equipos[1].faltas, MAX_FALTAS)

    def test_indices_invalidos_se_ignoran(self):
        for idx in (-1, 99, "x", None):
            self.assertFalse(self.estado.sumar_puntos(idx, 1))
            self.assertFalse(self.estado.sumar_faltas(idx, 1))

    def test_nombre_se_recorta(self):
        self.estado.renombrar(0, "X" * 200)
        self.assertLessEqual(len(self.estado.equipos[0].nombre), 40)

    def test_reiniciar_marcador_conserva_nombres(self):
        self.estado.renombrar(0, "AZULES")
        self.estado.sumar_puntos(0, 7)
        self.estado.sumar_faltas(0, 2)
        self.estado.reiniciar_marcador()
        self.assertEqual(self.estado.equipos[0].nombre, "AZULES")
        self.assertEqual(self.estado.equipos[0].puntos, 0)
        self.assertEqual(self.estado.equipos[0].faltas, 0)


class PruebasDeshacer(unittest.TestCase):
    def setUp(self):
        self.estado = EstadoPartido(num_equipos=2)

    def test_deshacer_un_punto_mal_dado(self):
        self.estado.sumar_puntos(0, 1)
        self.estado.sumar_puntos(1, 1)   # ¡se lo dimos al equipo equivocado!
        self.assertTrue(self.estado.deshacer())
        self.assertEqual(self.estado.equipos[1].puntos, 0)
        self.assertEqual(self.estado.equipos[0].puntos, 1)

    def test_rehacer_devuelve_lo_deshecho(self):
        self.estado.sumar_puntos(0, 3)
        self.estado.deshacer()
        self.assertTrue(self.estado.rehacer())
        self.assertEqual(self.estado.equipos[0].puntos, 3)

    def test_sin_historial_no_falla(self):
        self.assertFalse(self.estado.deshacer())
        self.assertFalse(self.estado.rehacer())

    def test_una_accion_nueva_borra_el_rehacer(self):
        self.estado.sumar_puntos(0, 1)
        self.estado.deshacer()
        self.estado.sumar_puntos(1, 1)
        self.assertFalse(self.estado.puede_rehacer)

    def test_las_faltas_tambien_se_deshacen(self):
        self.estado.sumar_faltas(0, 1)
        self.estado.deshacer()
        self.assertEqual(self.estado.equipos[0].faltas, 0)

    def test_el_historial_no_crece_sin_limite(self):
        for _ in range(500):
            self.estado.sumar_puntos(0, 1)
        self.assertLessEqual(len(self.estado._pila_deshacer), 60)

    def test_reiniciar_se_puede_deshacer(self):
        self.estado.sumar_puntos(0, 9)
        self.estado.reiniciar_marcador()
        self.estado.deshacer()
        self.assertEqual(self.estado.equipos[0].puntos, 9)


class PruebasPersistencia(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir.name, "cfg.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_ida_y_vuelta_completa(self):
        original = EstadoPartido(num_equipos=4)
        original.renombrar(0, "LOS TIGRES")
        original.pintar_equipo(0, "#123456")
        original.sumar_puntos(0, 12)
        original.sumar_faltas(0, 2)
        original.diseno.color_puntos = "#abcdef"
        original.diseno.scale_factor = 1.4
        original.diseno.ver_faltas = False
        original.diseno.corner_radius = 33
        original.sonidos[0].nombre = "BUZZER"
        original.sonidos[0].path = "/ruta/buzzer.wav"
        original.volumen = 0.35
        original.cronometro.fijar(150)

        guardar_json(original.a_dict(), self.ruta)
        copia = EstadoPartido(num_equipos=2)
        copia.aplicar_dict(cargar_json(self.ruta))

        self.assertEqual(len(copia.equipos), 4)
        self.assertEqual(copia.equipos[0].nombre, "LOS TIGRES")
        self.assertEqual(copia.equipos[0].color, "#123456")
        self.assertEqual(copia.equipos[0].puntos, 12)
        self.assertEqual(copia.equipos[0].faltas, 2)
        self.assertEqual(copia.diseno.color_puntos, "#abcdef")
        self.assertAlmostEqual(copia.diseno.scale_factor, 1.4)
        self.assertFalse(copia.diseno.ver_faltas)
        self.assertEqual(copia.diseno.corner_radius, 33)
        self.assertEqual(copia.sonidos[0].nombre, "BUZZER")
        self.assertEqual(copia.sonidos[0].path, "/ruta/buzzer.wav")
        self.assertAlmostEqual(copia.volumen, 0.35)
        self.assertEqual(copia.cronometro.restante, 150)

    def test_se_puede_cargar_solo_el_diseno(self):
        original = EstadoPartido()
        original.sumar_puntos(0, 5)
        guardar_json(original.a_dict(), self.ruta)
        copia = EstadoPartido()
        copia.aplicar_dict(cargar_json(self.ruta), incluir_marcador=False)
        self.assertEqual(copia.equipos[0].puntos, 0)

    def test_archivo_incompleto_no_rompe(self):
        estado = EstadoPartido()
        estado.aplicar_dict({"equipos": [{"nombre": "SOLO UNO"}]})
        self.assertEqual(estado.equipos[0].nombre, "SOLO UNO")
        self.assertEqual(estado.equipos[0].puntos, 0)

    def test_valores_corruptos_se_ignoran(self):
        estado = EstadoPartido()
        antes = estado.diseno.scale_factor
        estado.aplicar_dict({
            "diseno": {"scale_factor": "no-soy-un-numero", "clave_inventada": 1},
            "equipos": [{"nombre": "A", "puntos": "muchos", "faltas": 99}],
            "volumen": "alto",
        })
        self.assertEqual(estado.diseno.scale_factor, antes)
        self.assertEqual(estado.equipos[0].puntos, 0)

    def test_dict_invalido_lanza_error_claro(self):
        with self.assertRaises(ValueError):
            EstadoPartido().aplicar_dict("esto no es un preset")

    def test_faltas_fuera_de_rango_se_recortan(self):
        estado = EstadoPartido()
        estado.aplicar_dict({"equipos": [{"nombre": "A", "puntos": 5, "faltas": 77}]})
        self.assertEqual(estado.equipos[0].faltas, MAX_FALTAS)

    def test_guardado_atomico_no_deja_temporales(self):
        guardar_json({"hola": "mundo"}, self.ruta)
        self.assertEqual(os.listdir(self.dir.name), ["cfg.json"])

    def test_guardado_conserva_acentos(self):
        guardar_json({"equipo": "AZUL Ñ á"}, self.ruta)
        with open(self.ruta, encoding="utf-8") as f:
            self.assertIn("AZUL Ñ á", f.read())
        self.assertEqual(cargar_json(self.ruta)["equipo"], "AZUL Ñ á")

    def test_guardar_crea_la_carpeta(self):
        anidada = os.path.join(self.dir.name, "a", "b", "cfg.json")
        guardar_json({"x": 1}, anidada)
        self.assertTrue(os.path.isfile(anidada))

    def test_json_corrupto_lanza_error(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write("{ esto no es json")
        with self.assertRaises(json.JSONDecodeError):
            cargar_json(self.ruta)


class PruebasResumenRemoto(unittest.TestCase):
    def test_resumen_tiene_lo_que_el_celular_necesita(self):
        estado = EstadoPartido(num_equipos=2)
        estado.sumar_puntos(0, 4)
        resumen = estado.resumen()
        self.assertEqual(len(resumen['equipos']), 2)
        self.assertEqual(resumen['equipos'][0]['puntos'], 4)
        self.assertIn('color', resumen['equipos'][0])
        self.assertEqual(resumen['max_faltas'], MAX_FALTAS)
        self.assertTrue(resumen['puede_deshacer'])
        self.assertEqual(len(resumen['sonidos']), 6)
        self.assertFalse(resumen['timer']['corriendo'])

    def test_el_resumen_es_serializable(self):
        json.dumps(EstadoPartido().resumen())


class PruebasDiseno(unittest.TestCase):
    def test_aplicar_dict_respeta_tipos(self):
        d = Diseno()
        d.aplicar_dict({"corner_radius": "25", "scale_factor": "1.5", "ver_timer": 0,
                        "font_family": "Georgia"})
        self.assertIsInstance(d.corner_radius, int)
        self.assertEqual(d.corner_radius, 25)
        self.assertAlmostEqual(d.scale_factor, 1.5)
        self.assertFalse(d.ver_timer)
        self.assertEqual(d.font_family, "Georgia")


if __name__ == "__main__":
    unittest.main(verbosity=2)
