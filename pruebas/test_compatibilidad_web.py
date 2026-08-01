"""
Comprueba que la versión web y la de escritorio hablen el mismo idioma.

El formato de preset (`.json`) es compartido: un archivo guardado en el
programa de Windows debe abrirse en la web y al revés. Si alguien añade un
campo de diseño en un lado y lo olvida en el otro, estas pruebas fallan.

No necesitan navegador: leen el JavaScript como texto.
"""

import json
import os
import re
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from match_state import (  # noqa: E402
    MAX_EQUIPOS, MAX_FALTAS, MIN_EQUIPOS, NUM_SONIDOS, TIEMPO_MAXIMO,
    Diseno, EstadoPartido,
)

CARPETA_WEB = os.path.join(RAIZ, 'web')
ESTADO_JS = os.path.join(CARPETA_WEB, 'js', 'estado.js')


def leer(ruta):
    with open(ruta, encoding='utf-8') as f:
        return f.read()


class PruebasEstructuraWeb(unittest.TestCase):
    def test_existen_los_archivos_de_la_version_web(self):
        for relativo in ('index.html', 'tablero.html', 'css/estilos.css',
                         'js/estado.js', 'js/tablero.js', 'js/panel.js', 'js/almacen.js'):
            self.assertTrue(os.path.isfile(os.path.join(CARPETA_WEB, relativo)),
                            f'falta web/{relativo}')

    def test_la_version_web_no_depende_de_recursos_externos(self):
        """Debe funcionar sin internet una vez cargada (y sin rastreadores)."""
        for nombre in ('index.html', 'tablero.html'):
            texto = leer(os.path.join(CARPETA_WEB, nombre))
            # Se permiten enlaces de navegación y metadatos, pero no recursos.
            for etiqueta in re.findall(r'<(?:script|link)[^>]*>', texto):
                if 'rel="canonical"' in etiqueta or 'rel="icon"' in etiqueta:
                    continue
                self.assertNotIn('http://', etiqueta, f'{nombre}: recurso externo')
                self.assertNotIn('https://', etiqueta, f'{nombre}: recurso externo')


class PruebasParidadDeCampos(unittest.TestCase):
    """Los mismos nombres de campo a ambos lados."""

    def setUp(self):
        self.js = leer(ESTADO_JS)

    def claves_diseno_js(self):
        bloque = re.search(r'export const DISENO_POR_DEFECTO = \{(.*?)\n\};',
                           self.js, re.S)
        self.assertIsNotNone(bloque, 'no se encontró DISENO_POR_DEFECTO en estado.js')
        # Varias claves pueden compartir línea, así que no se ancla al principio.
        return set(re.findall(r'\b(\w+)\s*:', bloque.group(1)))

    def test_el_diseno_tiene_los_mismos_campos(self):
        del_python = {c.name for c in Diseno.__dataclass_fields__.values()}
        self.assertEqual(self.claves_diseno_js(), del_python)

    def test_las_constantes_coinciden(self):
        esperado = {
            'MAX_FALTAS': MAX_FALTAS, 'MAX_EQUIPOS': MAX_EQUIPOS,
            'MIN_EQUIPOS': MIN_EQUIPOS, 'NUM_SONIDOS': NUM_SONIDOS,
        }
        for nombre, valor in esperado.items():
            hallado = re.search(rf'export const {nombre} = (\d+)', self.js)
            self.assertIsNotNone(hallado, f'falta {nombre} en estado.js')
            self.assertEqual(int(hallado.group(1)), valor, f'{nombre} no coincide')

    def test_el_tiempo_maximo_coincide(self):
        hallado = re.search(r'export const TIEMPO_MAXIMO = 99 \* 60 \+ 59', self.js)
        self.assertIsNotNone(hallado)
        self.assertEqual(TIEMPO_MAXIMO, 99 * 60 + 59)

    def test_las_claves_enteras_estan_declaradas(self):
        """
        En JavaScript no se puede deducir si un campo es entero mirando su
        valor por defecto (Number.isInteger(1.0) es true), así que la lista
        debe mantenerse a mano y coincidir con los int reales de Python.
        """
        bloque = re.search(r'export const CLAVES_ENTERAS = new Set\(\[(.*?)\]\)',
                           self.js, re.S)
        self.assertIsNotNone(bloque, 'falta CLAVES_ENTERAS en estado.js')
        del_js = set(re.findall(r"'(\w+)'", bloque.group(1)))

        del_python = {
            campo.name for campo in Diseno.__dataclass_fields__.values()
            if campo.type in ('int', int)
        }
        self.assertEqual(del_js, del_python,
                         'la lista de campos enteros no coincide con la de Python')


class PruebasPresetCompartido(unittest.TestCase):
    """Un preset de escritorio debe ser legible por el modelo, ida y vuelta."""

    def test_las_claves_de_nivel_superior_son_las_esperadas(self):
        datos = EstadoPartido().a_dict()
        self.assertEqual(set(datos), {'version', 'equipos', 'diseno',
                                      'sonidos', 'volumen', 'duracion_timer'})
        self.assertEqual(datos['version'], 2)

    def test_un_preset_de_la_web_se_carga_sin_perder_decimales(self):
        # Reproduce lo que exporta el navegador (mismo formato, tipos de JS).
        preset_web = {
            'version': 2,
            'equipos': [{'nombre': 'WEB', 'color': '#ff0055', 'puntos': 3, 'faltas': 1},
                        {'nombre': 'OTRO', 'color': '#1f6feb', 'puntos': 0, 'faltas': 0}],
            'diseno': {'scale_factor': 1.35, 'corner_radius': 42,
                       'timer_position': 'Arriba', 'ver_faltas': False},
            'sonidos': [{'nombre': 'CHICHARRA', 'path': 'buzzer.wav'}],
            'volumen': 0.55,
            'duracion_timer': 210,
        }
        estado = EstadoPartido()
        estado.aplicar_dict(preset_web)
        self.assertEqual(len(estado.equipos), 2)
        self.assertEqual(estado.equipos[0].nombre, 'WEB')
        self.assertAlmostEqual(estado.diseno.scale_factor, 1.35)
        self.assertEqual(estado.diseno.corner_radius, 42)
        self.assertIsInstance(estado.diseno.corner_radius, int)
        self.assertFalse(estado.diseno.ver_faltas)
        self.assertEqual(estado.cronometro.restante, 210)

    def test_el_preset_de_escritorio_es_json_plano(self):
        """Sin tipos raros: el navegador debe poder leerlo con JSON.parse."""
        estado = EstadoPartido(4)
        estado.diseno.scale_factor = 1.25
        texto = json.dumps(estado.a_dict())
        self.assertEqual(json.loads(texto)['diseno']['scale_factor'], 1.25)


if __name__ == '__main__':
    unittest.main(verbosity=2)
