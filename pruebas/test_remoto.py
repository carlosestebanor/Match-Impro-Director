"""
Pruebas del mando a distancia: servidor HTTP, PIN y cola de comandos.
No necesitan pantalla ni audio.
"""

import json
import os
import socket
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from remote_control import ControlRemoto, generar_pin, obtener_ip_local  # noqa: E402

PIN = "123456"


def puerto_libre():
    """Pide al sistema un puerto disponible para no chocar entre pruebas."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


ESTADO_DEMO = {
    'equipos': [{'nombre': 'ROJO', 'puntos': 3, 'faltas': 1, 'color': '#e02020'},
                {'nombre': 'AZUL', 'puntos': 5, 'faltas': 0, 'color': '#1f6feb'}],
    'timer': {'restante': 240, 'corriendo': False},
    'sonidos': [{'nombre': f'FX {i + 1}', 'cargado': i == 0} for i in range(6)],
    'max_faltas': 3,
    'puede_deshacer': False,
}


class BaseServidor(unittest.TestCase):
    def setUp(self):
        self.puerto = puerto_libre()
        self.remoto = ControlRemoto(lambda: ESTADO_DEMO, puerto=self.puerto, pin=PIN)
        self.remoto.iniciar()
        self.base = f"http://127.0.0.1:{self.puerto}"

    def tearDown(self):
        self.remoto.detener()

    def pedir(self, ruta, pin=None, cuerpo=None, metodo=None):
        req = urllib.request.Request(self.base + ruta, data=cuerpo, method=metodo)
        if pin is not None:
            req.add_header("X-Match-Pin", pin)
        if cuerpo:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def enviar_comando(self, comando, pin=PIN):
        return self.pedir("/api/comando", pin=pin, cuerpo=json.dumps(comando).encode())[0]


class PruebasPagina(BaseServidor):
    def test_la_pagina_se_sirve_sin_pin(self):
        codigo, cuerpo = self.pedir("/")
        self.assertEqual(codigo, 200)
        self.assertIn("CONTROL REMOTO", cuerpo)

    def test_la_pagina_no_pide_recursos_externos(self):
        """Debe funcionar sin internet: todo va embebido."""
        _, cuerpo = self.pedir("/")
        for señal in ("http://", "https://", "<script src", "<link rel=\"stylesheet\""):
            self.assertNotIn(señal, cuerpo)

    def test_favicon_responde_sin_contenido(self):
        codigo, _ = self.pedir("/favicon.ico")
        self.assertEqual(codigo, 204)

    def test_ruta_desconocida(self):
        self.assertEqual(self.pedir("/lo-que-sea", pin=PIN)[0], 404)


class PruebasAutenticacion(BaseServidor):
    def test_sin_pin_no_se_lee_el_estado(self):
        self.assertEqual(self.pedir("/api/estado")[0], 401)

    def test_pin_incorrecto(self):
        self.assertEqual(self.pedir("/api/estado", pin="000000")[0], 401)

    def test_pin_vacio(self):
        self.assertEqual(self.pedir("/api/estado", pin="")[0], 401)

    def test_pin_correcto_devuelve_el_estado(self):
        codigo, cuerpo = self.pedir("/api/estado", pin=PIN)
        self.assertEqual(codigo, 200)
        datos = json.loads(cuerpo)
        self.assertEqual(datos['equipos'][1]['puntos'], 5)
        self.assertEqual(datos['max_faltas'], 3)

    def test_sin_pin_no_se_encolan_comandos(self):
        self.assertEqual(self.enviar_comando({"accion": "puntos"}, pin=None), 401)
        self.assertEqual(self.remoto.vaciar_comandos(), [])

    def test_cambiar_el_pin_invalida_el_anterior(self):
        viejo = self.remoto.pin
        self.remoto.pin = generar_pin()
        self.assertEqual(self.pedir("/api/estado", pin=viejo)[0], 401)
        self.assertEqual(self.pedir("/api/estado", pin=self.remoto.pin)[0], 200)

    def test_el_pin_generado_tiene_seis_digitos(self):
        for _ in range(50):
            pin = generar_pin()
            self.assertEqual(len(pin), 6)
            self.assertTrue(pin.isdigit())


class PruebasComandos(BaseServidor):
    def test_un_comando_llega_a_la_cola(self):
        self.assertEqual(self.enviar_comando({"accion": "puntos", "equipo": 0, "delta": 1}), 200)
        self.assertEqual(self.remoto.vaciar_comandos(),
                         [{"accion": "puntos", "equipo": 0, "delta": 1}])

    def test_la_cola_se_vacia_al_leerla(self):
        self.enviar_comando({"accion": "deshacer"})
        self.remoto.vaciar_comandos()
        self.assertEqual(self.remoto.vaciar_comandos(), [])

    def test_se_conserva_el_orden(self):
        for i in range(5):
            self.enviar_comando({"accion": "puntos", "equipo": i})
        recibidos = [c["equipo"] for c in self.remoto.vaciar_comandos()]
        self.assertEqual(recibidos, [0, 1, 2, 3, 4])

    def test_json_invalido(self):
        self.assertEqual(self.pedir("/api/comando", pin=PIN, cuerpo=b"no soy json")[0], 400)

    def test_cuerpo_vacio(self):
        self.assertEqual(self.pedir("/api/comando", pin=PIN, cuerpo=b"")[0], 400)

    def test_json_que_no_es_objeto(self):
        self.assertEqual(self.pedir("/api/comando", pin=PIN, cuerpo=b"[1,2,3]")[0], 400)

    def test_cuerpo_gigante_se_rechaza(self):
        enorme = json.dumps({"accion": "x", "relleno": "A" * 20000}).encode()
        self.assertEqual(self.pedir("/api/comando", pin=PIN, cuerpo=enorme)[0], 400)

    def test_la_cola_tiene_tope(self):
        for _ in range(260):
            self.enviar_comando({"accion": "puntos", "equipo": 0})
        self.assertLessEqual(len(self.remoto.vaciar_comandos()), 200)

    def test_post_a_otra_ruta(self):
        self.assertEqual(self.pedir("/api/otra", pin=PIN, cuerpo=b"{}")[0], 404)

    def test_varios_celulares_a_la_vez(self):
        """Dos mandos en paralelo no deben perder comandos."""
        def enviar(n):
            for i in range(10):
                self.enviar_comando({"accion": "puntos", "equipo": n, "orden": i})

        hilos = [threading.Thread(target=enviar, args=(n,)) for n in (0, 1)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(len(self.remoto.vaciar_comandos()), 20)


class PruebasCicloDeVida(unittest.TestCase):
    def test_puerto_ocupado_lanza_oserror(self):
        puerto = puerto_libre()
        primero = ControlRemoto(lambda: ESTADO_DEMO, puerto=puerto, pin=PIN)
        primero.iniciar()
        segundo = ControlRemoto(lambda: ESTADO_DEMO, puerto=puerto, pin=PIN)
        try:
            with self.assertRaises(OSError):
                segundo.iniciar()
        finally:
            primero.detener()

    def test_apagar_y_encender(self):
        remoto = ControlRemoto(lambda: ESTADO_DEMO, puerto=puerto_libre(), pin=PIN)
        remoto.iniciar()
        self.assertTrue(remoto.activo)
        remoto.detener()
        self.assertFalse(remoto.activo)
        remoto.iniciar()
        self.assertTrue(remoto.activo)
        remoto.detener()

    def test_detener_dos_veces_no_falla(self):
        remoto = ControlRemoto(lambda: ESTADO_DEMO, puerto=puerto_libre(), pin=PIN)
        remoto.iniciar()
        remoto.detener()
        remoto.detener()

    def test_apagado_limpia_la_cola(self):
        remoto = ControlRemoto(lambda: ESTADO_DEMO, puerto=puerto_libre(), pin=PIN)
        remoto.iniciar()
        remoto.encolar({"accion": "puntos"})
        remoto.detener()
        self.assertEqual(remoto.vaciar_comandos(), [])

    def test_la_url_incluye_ip_y_puerto(self):
        remoto = ControlRemoto(lambda: ESTADO_DEMO, puerto=9999, pin=PIN)
        self.assertTrue(remoto.url.startswith("http://"))
        self.assertTrue(remoto.url.endswith(":9999"))

    def test_ip_local_tiene_forma_de_ip(self):
        partes = obtener_ip_local().split(".")
        self.assertEqual(len(partes), 4)
        self.assertTrue(all(p.isdigit() for p in partes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
