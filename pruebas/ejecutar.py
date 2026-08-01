"""
Lanza todas las pruebas del proyecto.

    python pruebas/ejecutar.py            # todo
    python pruebas/ejecutar.py --sin-gui  # solo lo que no necesita pantalla

En Linux sin escritorio, las pruebas gráficas necesitan un servidor X virtual:

    xvfb-run -a python pruebas/ejecutar.py
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

MODULOS_SIN_GUI = ["pruebas.test_estado", "pruebas.test_remoto",
                   "pruebas.test_compatibilidad_web"]
MODULOS_CON_GUI = ["pruebas.test_tablero", "pruebas.test_app"]


def hay_pantalla():
    if sys.platform != "linux":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def main():
    solo_sin_gui = "--sin-gui" in sys.argv
    modulos = list(MODULOS_SIN_GUI)

    if solo_sin_gui:
        print("Modo --sin-gui: se omiten las pruebas de tablero e interfaz.\n")
    elif not hay_pantalla():
        print("AVISO: no se detectó pantalla (DISPLAY). Se omiten las pruebas gráficas.")
        print("       Usa 'xvfb-run -a python pruebas/ejecutar.py' para ejecutarlas.\n")
    else:
        modulos += MODULOS_CON_GUI

    cargador = unittest.TestLoader()
    suite = unittest.TestSuite(cargador.loadTestsFromNames(modulos))
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)

    print()
    print(f"Pruebas ejecutadas: {resultado.testsRun}")
    print(f"Fallos: {len(resultado.failures)} | Errores: {len(resultado.errors)}")
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
