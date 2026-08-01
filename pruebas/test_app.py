"""
Pruebas de la aplicación completa: panel, atajos, preferencias y puente remoto.
Necesitan una pantalla (real o virtual con xvfb-run).
"""

import json
import os
import sys
import tempfile
import time
import tkinter as tk
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)


class BaseApp(unittest.TestCase):
    """Levanta la app real contra un archivo de preferencias desechable."""

    contenido_config = None   # Las subclases pueden dejar un preset preparado

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.config = os.path.join(self.dir.name, "cfg.json")
        if self.contenido_config is not None:
            with open(self.config, "w", encoding="utf-8") as f:
                json.dump(self.contenido_config, f)
        os.environ["MATCH_DIRECTOR_CONFIG"] = self.config

        import match_director_source as mds
        self.mds = mds
        self.app = mds.ImproMatchApp(iniciar_bucle=False)
        self.girar(0.2)

    def tearDown(self):
        try:
            if self.app.root.winfo_exists():
                self.app.cerrar_app()
        except tk.TclError:
            pass
        os.environ.pop("MATCH_DIRECTOR_CONFIG", None)
        self.dir.cleanup()

    def girar(self, segundos=0.25):
        """Deja correr el bucle de Tk para que se procesen los callbacks."""
        fin = time.time() + segundos
        while time.time() < fin:
            try:
                self.app.root.update()
            except tk.TclError:
                return
            time.sleep(0.01)

    def enviar_tecla(self, secuencia, widget=None):
        # Tk solo entrega eventos de teclado a la ventana con el foco del sistema.
        destino = widget or self.app.root
        destino.focus_force()
        self.girar(0.1)
        destino.event_generate(secuencia)
        self.girar(0.12)

    def esperar_reposo(self):
        """Deja que terminen los refinados y autoguardados pendientes."""
        self.girar((self.mds.REFINAR_MS / 1000) + 0.35)


class PruebasArranque(BaseApp):
    def test_abre_las_dos_ventanas(self):
        self.assertTrue(self.app.root.winfo_exists())
        self.assertTrue(self.app.win_proj.winfo_exists())

    def test_dibuja_el_tablero_al_arrancar(self):
        self.assertGreater(len(self.app.canvas.find_all()), 10)

    def test_el_panel_muestra_los_equipos(self):
        self.assertEqual(len(self.app.entries_nombres), 3)
        self.assertEqual(self.app.entries_nombres[0].get(), "ROJO")

    def test_hay_seis_botones_de_efectos(self):
        self.assertEqual(len(self.app.botones_sonido_live), 6)

    def test_el_reloj_del_panel_arranca_en_cuatro_minutos(self):
        self.assertEqual(self.app.lbl_reloj.cget("text"), "04:00")


class PruebasMarcador(BaseApp):
    def test_sumar_y_restar_puntos(self):
        self.app.mod(0, 1, 'p')
        self.app.mod(0, 1, 'p')
        self.girar()
        self.assertEqual(self.app.estado.equipos[0].puntos, 2)
        self.assertEqual(self.app.lbls_puntos_ctrl[0].cget("text"), "2")
        self.app.mod(0, -1, 'p')
        self.girar()
        self.assertEqual(self.app.lbls_puntos_ctrl[0].cget("text"), "1")

    def test_los_puntos_llegan_al_tablero(self):
        self.app.mod(1, 1, 'p')
        self.girar()
        textos = [self.app.canvas.itemcget(i, "text") for i in self.app.canvas.find_all()
                  if self.app.canvas.type(i) == "text"]
        self.assertIn("1", textos)

    def test_deshacer_y_rehacer_desde_el_panel(self):
        self.app.mod(0, 1, 'p')
        self.girar()
        self.app.deshacer()
        self.girar()
        self.assertEqual(self.app.estado.equipos[0].puntos, 0)
        self.assertEqual(self.app.lbls_puntos_ctrl[0].cget("text"), "0")
        self.app.rehacer()
        self.girar()
        self.assertEqual(self.app.estado.equipos[0].puntos, 1)

    def test_los_botones_de_historial_se_habilitan_solos(self):
        self.assertEqual(str(self.app.btn_deshacer.cget("state")), "disabled")
        self.app.mod(0, 1, 'p')
        self.girar()
        self.assertEqual(str(self.app.btn_deshacer.cget("state")), "normal")

    def test_cambiar_numero_de_equipos_rehace_las_tiras(self):
        self.app.num_equipos_var.set(5)
        self.app.actualizar_estructura_equipos()
        self.girar()
        self.assertEqual(len(self.app.estado.equipos), 5)
        self.assertEqual(len(self.app.entries_nombres), 5)
        self.assertEqual(len(self.app.botones_color), 5)

    def test_reiniciar_marcador_con_confirmacion(self):
        self.app.mod(0, 1, 'p')
        self.app.mod(0, 1, 'f')
        self.girar()
        self.mds.messagebox.askyesno = lambda *a, **k: True
        self.app.reiniciar_marcador()
        self.girar()
        self.assertEqual(self.app.estado.equipos[0].puntos, 0)
        self.assertEqual(self.app.estado.equipos[0].faltas, 0)

    def test_reiniciar_cancelado_no_toca_nada(self):
        self.app.mod(0, 3, 'p')
        self.girar()
        self.mds.messagebox.askyesno = lambda *a, **k: False
        self.app.reiniciar_marcador()
        self.girar()
        self.assertEqual(self.app.estado.equipos[0].puntos, 3)

    def test_renombrar_equipo_desde_el_panel(self):
        self.app.entries_nombres[0].delete(0, "end")
        self.app.entries_nombres[0].insert(0, "LOS GATOS")
        self.app.actualizar_nombre_live(0)
        self.girar()
        self.assertEqual(self.app.estado.equipos[0].nombre, "LOS GATOS")
        textos = [self.app.canvas.itemcget(i, "text") for i in self.app.canvas.find_all()
                  if self.app.canvas.type(i) == "text"]
        self.assertIn("LOS GATOS", textos)


class PruebasCronometro(BaseApp):
    def test_set_lee_las_casillas(self):
        self.app.e_min.delete(0, "end"); self.app.e_min.insert(0, "2")
        self.app.e_sec.delete(0, "end"); self.app.e_sec.insert(0, "30")
        self.app.set_tiempo()
        self.girar()
        self.assertEqual(self.app.estado.cronometro.restante, 150)
        self.assertEqual(self.app.lbl_reloj.cget("text"), "02:30")

    def test_set_con_texto_invalido_avisa_y_no_rompe(self):
        antes = self.app.estado.cronometro.restante
        self.app.e_min.delete(0, "end"); self.app.e_min.insert(0, "abc")
        self.app.set_tiempo()
        self.girar()
        self.assertEqual(self.app.estado.cronometro.restante, antes)
        self.assertIn("números", self.app.estado_var.get())

    def test_set_con_segundos_fuera_de_rango_avisa(self):
        self.app.e_sec.delete(0, "end"); self.app.e_sec.insert(0, "88")
        self.app.set_tiempo()
        self.girar()
        self.assertIn("0 a 59", self.app.estado_var.get())

    def test_iniciar_y_pausar(self):
        self.app.iniciar_tiempo()
        self.assertTrue(self.app.estado.cronometro.corriendo)
        self.app.pausar_tiempo()
        self.assertFalse(self.app.estado.cronometro.corriendo)

    def test_ajustes_rapidos(self):
        self.app.ajustar_tiempo(30)
        self.girar()
        self.assertEqual(self.app.estado.cronometro.restante, 270)
        self.assertEqual(self.app.e_min.get(), "4")
        self.assertEqual(self.app.e_sec.get(), "30")

    def test_el_reloj_del_panel_avanza_solo(self):
        self.app.estado.cronometro.fijar(10)
        self.app.iniciar_tiempo()
        self.girar(1.4)
        self.assertIn(self.app.lbl_reloj.cget("text"), ("00:09", "00:08"))

    def test_no_inicia_si_el_reloj_esta_en_cero(self):
        self.app.estado.cronometro.fijar(0)
        self.app.iniciar_tiempo()
        self.girar()
        self.assertFalse(self.app.estado.cronometro.corriendo)
        self.assertIn("SET", self.app.estado_var.get())


class PruebasAtajos(BaseApp):
    def test_espacio_inicia_y_pausa(self):
        self.app.root.focus_set()
        self.enviar_tecla("<space>")
        self.assertTrue(self.app.estado.cronometro.corriendo)
        self.enviar_tecla("<space>")
        self.assertFalse(self.app.estado.cronometro.corriendo)

    def test_numeros_suman_puntos(self):
        self.app.root.focus_set()
        self.enviar_tecla("<Key-2>")
        self.assertEqual(self.app.estado.equipos[1].puntos, 1)

    def test_efe_marca_falta(self):
        self.enviar_tecla("<F1>")
        self.assertEqual(self.app.estado.equipos[0].faltas, 1)

    def test_control_z_deshace(self):
        self.app.mod(0, 1, 'p')
        self.girar()
        self.enviar_tecla("<Control-z>")
        self.assertEqual(self.app.estado.equipos[0].puntos, 0)

    def test_los_atajos_se_ignoran_al_escribir(self):
        entrada = self.app.entries_nombres[0]
        entrada.focus_set()
        self.girar(0.15)
        antes = self.app.estado.equipos[1].puntos
        self.enviar_tecla("<Key-2>", entrada)
        self.assertEqual(self.app.estado.equipos[1].puntos, antes)
        self.assertFalse(self.app.estado.cronometro.corriendo)

    def test_control_s_guarda(self):
        self.app.atajo_guardar()
        self.assertTrue(os.path.isfile(self.config))
        self.assertIn("guardadas", self.app.estado_var.get())


class PruebasPantallaCompleta(BaseApp):
    def test_alternar_y_salir(self):
        self.app.alternar_pantalla_completa()
        self.girar()
        self.assertTrue(self.app.is_fullscreen)
        self.app.salir_pantalla_completa()
        self.girar()
        self.assertFalse(self.app.is_fullscreen)

    def test_escape_sale_de_pantalla_completa(self):
        self.app.poner_pantalla_completa(True)
        self.girar()
        self.enviar_tecla("<Escape>")
        self.assertFalse(self.app.is_fullscreen)

    def test_el_tablero_se_redibuja_al_cambiar_de_tamano(self):
        self.app.win_proj.geometry("1024x600")
        self.girar(0.6)
        self.assertGreater(len(self.app.canvas.find_all()), 10)


class PruebasRendimientoPanel(BaseApp):
    def test_varias_solicitudes_producen_un_solo_redibujado(self):
        self.esperar_reposo()
        contador = {'n': 0}
        original = self.app.redibujar_ahora

        def espia(*a, **k):
            contador['n'] += 1
            return original(*a, **k)

        self.app.redibujar_ahora = espia
        for _ in range(10):
            self.app.solicitar_redibujado()
        self.girar(0.3)
        self.assertEqual(contador['n'], 1)

    def test_en_reposo_no_se_redibuja_nada(self):
        self.esperar_reposo()
        contador = {'n': 0}
        original = self.app.redibujar_ahora
        self.app.redibujar_ahora = lambda *a, **k: (contador.__setitem__('n', contador['n'] + 1),
                                                    original(*a, **k))[1]
        self.girar(0.6)
        self.assertEqual(contador['n'], 0)

    def test_el_tic_no_redibuja_el_tablero_entero(self):
        self.app.estado.cronometro.fijar(30)
        self.app.iniciar_tiempo()
        self.girar(0.3)
        ids_antes = self.app.canvas.find_all()
        self.girar(1.3)   # Pasa al menos un segundo de reloj
        self.assertEqual(ids_antes, self.app.canvas.find_all())


class PruebasVistaPrevia(BaseApp):
    """La miniatura de 'lo que ve el público' dentro del panel."""

    def test_se_dibuja_al_arrancar(self):
        self.assertGreater(len(self.app.canvas_preview.find_all()), 10)

    def test_refleja_el_marcador(self):
        self.app.mod(0, 1, 'p')
        self.app.mod(0, 1, 'p')
        self.girar()
        textos = [self.app.canvas_preview.itemcget(i, "text")
                  for i in self.app.canvas_preview.find_all()
                  if self.app.canvas_preview.type(i) == "text"]
        self.assertIn("2", textos)

    def test_respeta_la_proporcion_del_proyector(self):
        self.app.win_proj.geometry("1200x600")
        self.girar(0.6)
        alto = int(self.app.canvas_preview.cget("height"))
        esperado = int(self.mds.PREVIEW_ANCHO * 600 / 1200)
        self.assertAlmostEqual(alto, esperado, delta=6)

    def test_se_puede_ocultar(self):
        self.app.ver_preview.set(False)
        self.app.alternar_vista_previa()
        self.girar()
        self.assertFalse(self.app.canvas_preview.winfo_ismapped())

    def test_oculta_no_consume_dibujo(self):
        self.app.ver_preview.set(False)
        self.app.alternar_vista_previa()
        self.app.canvas_preview.delete("all")
        self.app.redibujar_ahora()
        self.girar()
        self.assertEqual(len(self.app.canvas_preview.find_all()), 0)

    def test_vuelve_al_mostrarla(self):
        self.app.ver_preview.set(False)
        self.app.alternar_vista_previa()
        self.girar()
        self.app.ver_preview.set(True)
        self.app.alternar_vista_previa()
        self.girar()
        self.assertTrue(self.app.canvas_preview.winfo_ismapped())
        self.assertGreater(len(self.app.canvas_preview.find_all()), 10)

    def test_el_reloj_de_la_miniatura_avanza(self):
        self.app.estado.cronometro.fijar(65)
        self.girar(0.4)
        textos = [self.app.canvas_preview.itemcget(i, "text")
                  for i in self.app.canvas_preview.find_all()
                  if self.app.canvas_preview.type(i) == "text"]
        self.assertIn("01:05", textos)


class PruebasSemaforoFaltas(BaseApp):
    """El panel debe mostrar las faltas, no solo el proyector."""

    def test_hay_tres_luces_por_equipo(self):
        self.assertEqual(len(self.app.luces_faltas), 3)
        self.assertTrue(all(len(l) == self.mds.MAX_FALTAS for l in self.app.luces_faltas))

    def test_se_encienden_al_marcar_falta(self):
        apagado = self.app.luces_faltas[0][0].cget("fg")
        self.app.mod(0, 1, 'f')
        self.girar()
        self.assertEqual(self.app.luces_faltas[0][0].cget("fg"),
                         self.app.estado.diseno.color_faltas)
        self.assertEqual(self.app.luces_faltas[0][1].cget("fg"), apagado)

    def test_se_apagan_al_quitar_falta(self):
        self.app.mod(1, 1, 'f')
        self.girar()
        self.app.mod(1, -1, 'f')
        self.girar()
        self.assertNotEqual(self.app.luces_faltas[1][0].cget("fg"),
                            self.app.estado.diseno.color_faltas)

    def test_se_rehacen_al_cambiar_de_equipos(self):
        self.app.num_equipos_var.set(5)
        self.app.actualizar_estructura_equipos()
        self.girar()
        self.assertEqual(len(self.app.luces_faltas), 5)


class PruebasBarraDeEstado(BaseApp):
    def test_los_avisos_llevan_color_segun_importancia(self):
        self.app.avisar("todo bien", 'ok')
        self.assertEqual(self.app.lbl_estado.cget("fg"), self.mds.AVISO_OK)
        self.app.avisar("cuidado", 'alerta')
        self.assertEqual(self.app.lbl_estado.cget("fg"), self.mds.AVISO_ALERTA)
        self.app.avisar("mal", 'error')
        self.assertEqual(self.app.lbl_estado.cget("fg"), self.mds.AVISO_ERROR)
        self.app.avisar("normal")
        self.assertEqual(self.app.lbl_estado.cget("fg"), self.mds.TEXTO_TENUE)

    def test_un_error_de_tiempo_se_marca_como_error(self):
        self.app.e_min.delete(0, "end"); self.app.e_min.insert(0, "xx")
        self.app.set_tiempo()
        self.girar()
        self.assertEqual(self.app.lbl_estado.cget("fg"), self.mds.AVISO_ERROR)


class PruebasImagenes(BaseApp):
    def test_quitar_fondo_y_logo(self):
        self.app.estado.diseno.fondo_path = "/inventado/fondo.png"
        self.app.estado.diseno.logo_path = "/inventado/logo.png"
        self.app.quitar_fondo()
        self.app.quitar_logo()
        self.girar()
        self.assertEqual(self.app.estado.diseno.fondo_path, "")
        self.assertEqual(self.app.estado.diseno.logo_path, "")

    def test_una_ruta_rota_no_tumba_el_tablero(self):
        self.app.estado.diseno.fondo_path = "/no/existe.png"
        self.app.redibujar_ahora()
        self.girar()
        self.assertGreater(len(self.app.canvas.find_all()), 10)


class PruebasSonidos(BaseApp):
    def test_disparar_un_slot_vacio_solo_avisa(self):
        self.app.play_sound(0)
        self.girar()
        self.assertIn("no tiene", self.app.estado_var.get())

    def test_renombrar_un_efecto_actualiza_el_boton(self):
        self.app.update_sound_name(0, "BUZZER")
        self.assertEqual(self.app.botones_sonido_live[0].cget("text"), "BUZZER")
        self.assertEqual(self.app.estado.sonidos[0].nombre, "BUZZER")

    def test_vaciar_un_slot(self):
        self.app.estado.sonidos[0].path = "/algo.wav"
        self.app.vaciar_sonido(0)
        self.assertEqual(self.app.estado.sonidos[0].path, "")

    def test_el_volumen_queda_guardado(self):
        self.app.cambiar_volumen("40")
        self.assertAlmostEqual(self.app.estado.volumen, 0.4)

    def test_detener_sonidos_no_falla_sin_audio(self):
        self.app.detener_sonidos()
        self.assertIn("detenidos", self.app.estado_var.get())


class PruebasPreferencias(BaseApp):
    def test_al_cerrar_se_guardan(self):
        self.app.renombrar = None
        self.app.estado.renombrar(0, "PERSISTENTES")
        self.app.cerrar_app()
        with open(self.config, encoding="utf-8") as f:
            datos = json.load(f)
        self.assertEqual(datos['equipos'][0]['nombre'], "PERSISTENTES")

    def test_el_autoguardado_escribe_el_archivo(self):
        self.app.estado.diseno.scale_factor = 1.75
        self.app.programar_autoguardado()
        self.girar(self.mds.AUTOGUARDADO_MS / 1000 + 0.6)
        with open(self.config, encoding="utf-8") as f:
            datos = json.load(f)
        self.assertAlmostEqual(datos['diseno']['scale_factor'], 1.75)

    def test_guardar_en_ruta_de_solo_lectura_no_tumba_la_app(self):
        self.assertFalse(self.app.guardar_preferencias("/proc/imposible/cfg.json"))
        self.assertTrue(self.app.root.winfo_exists())

    def test_preferencias_corruptas_no_impiden_arrancar(self):
        with open(self.config, "w", encoding="utf-8") as f:
            f.write("{{{ roto")
        self.assertFalse(self.app.cargar_preferencias(silencioso=True))
        self.assertTrue(self.app.root.winfo_exists())


class PruebasArranqueConPreset(BaseApp):
    """La app debe abrir tal como quedó la función anterior."""

    contenido_config = {
        "version": 2,
        "equipos": [
            {"nombre": "LOS RAPIDOS", "color": "#ff00ff", "puntos": 6, "faltas": 1},
            {"nombre": "LOS LENTOS", "color": "#00ffff", "puntos": 4, "faltas": 0},
            {"nombre": "TERCEROS", "color": "#ffff00", "puntos": 0, "faltas": 0},
            {"nombre": "CUARTOS", "color": "#00ff00", "puntos": 0, "faltas": 0},
        ],
        "diseno": {"color_puntos": "#abcdef", "timer_position": "Arriba",
                   "ver_faltas": False, "scale_factor": 1.3, "segundos_alerta": 20},
        "sonidos": [{"nombre": "CHICHARRA", "path": ""}],
        "volumen": 0.5,
        "duracion_timer": 180,
    }

    def test_recupera_equipos_y_marcador(self):
        self.assertEqual(len(self.app.estado.equipos), 4)
        self.assertEqual(self.app.estado.equipos[0].nombre, "LOS RAPIDOS")
        self.assertEqual(self.app.estado.equipos[0].puntos, 6)
        self.assertEqual(self.app.entries_nombres[0].get(), "LOS RAPIDOS")

    def test_el_spinbox_coincide_con_los_equipos_cargados(self):
        self.assertEqual(self.app.num_equipos_var.get(), 4)

    def test_recupera_el_diseno(self):
        self.assertEqual(self.app.estado.diseno.color_puntos, "#abcdef")
        self.assertEqual(self.app.combo_timer.get(), "Arriba")
        self.assertFalse(self.app.ver_faltas.get())
        self.assertEqual(self.app.spin_alerta.get(), "20")

    def test_recupera_reloj_y_volumen(self):
        self.assertEqual(self.app.estado.cronometro.restante, 180)
        self.assertEqual(self.app.lbl_reloj.cget("text"), "03:00")
        self.assertEqual(self.app.scale_volumen.get(), 50)

    def test_recupera_nombres_de_efectos(self):
        self.assertEqual(self.app.botones_sonido_live[0].cget("text"), "CHICHARRA")

    def test_cargar_un_preset_en_caliente(self):
        otro = os.path.join(self.dir.name, "otro.json")
        with open(otro, "w", encoding="utf-8") as f:
            json.dump({"equipos": [{"nombre": "A", "color": "#111111"},
                                   {"nombre": "B", "color": "#222222"}],
                       "diseno": {"color_puntos": "#010203"},
                       "duracion_timer": 60}, f)
        self.assertTrue(self.app.cargar_preferencias(otro))
        self.app.aplicar_estado_a_la_interfaz()
        self.girar()
        self.assertEqual(len(self.app.entries_nombres), 2)
        self.assertEqual(self.app.entries_nombres[0].get(), "A")
        self.assertEqual(self.app.estado.diseno.color_puntos, "#010203")
        self.assertEqual(self.app.lbl_reloj.cget("text"), "01:00")


class PruebasPuenteRemoto(BaseApp):
    """Comandos que llegan del celular, aplicados en el hilo de Tk."""

    def aplicar(self, comando):
        self.app.aplicar_comando_remoto(comando)
        self.girar(0.12)

    def test_estado_para_remoto_es_serializable(self):
        json.dumps(self.app.estado_para_remoto())

    def test_puntos_y_faltas(self):
        self.aplicar({"accion": "puntos", "equipo": 0, "delta": 1})
        self.assertEqual(self.app.estado.equipos[0].puntos, 1)
        self.assertEqual(self.app.lbls_puntos_ctrl[0].cget("text"), "1")
        self.aplicar({"accion": "faltas", "equipo": 0, "delta": 1})
        self.assertEqual(self.app.estado.equipos[0].faltas, 1)

    def test_cronometro_por_control_remoto(self):
        self.aplicar({"accion": "timer_set", "segundos": 90})
        self.assertEqual(self.app.estado.cronometro.restante, 90)
        self.assertEqual(self.app.e_min.get(), "1")
        self.aplicar({"accion": "timer_start"})
        self.assertTrue(self.app.estado.cronometro.corriendo)
        self.aplicar({"accion": "timer_pause"})
        self.assertFalse(self.app.estado.cronometro.corriendo)

    def test_ajuste_rapido_por_control_remoto(self):
        self.aplicar({"accion": "timer_set", "segundos": 100})
        self.aplicar({"accion": "timer_ajustar", "segundos": -30})
        self.assertEqual(self.app.estado.cronometro.restante, 70)

    def test_deshacer_por_control_remoto(self):
        self.aplicar({"accion": "puntos", "equipo": 0, "delta": 1})
        self.aplicar({"accion": "deshacer"})
        self.assertEqual(self.app.estado.equipos[0].puntos, 0)

    def test_detener_sonidos_por_control_remoto(self):
        self.aplicar({"accion": "detener_sonidos"})
        self.assertTrue(self.app.root.winfo_exists())

    def test_comandos_basura_no_tumban_la_app(self):
        antes = self.app.estado.equipos[0].puntos
        for basura in ({"accion": "puntos", "equipo": 99, "delta": 1},
                       {"accion": "puntos", "equipo": -3, "delta": 1},
                       {"accion": "puntos", "equipo": "x", "delta": 1},
                       {"accion": "sonido", "slot": 77},
                       {"accion": "inventada"},
                       {}):
            try:
                self.aplicar(basura)
            except Exception:
                pass
        self.assertEqual(self.app.estado.equipos[0].puntos, antes)
        self.assertTrue(self.app.root.winfo_exists())

    def test_el_bombeo_tolera_el_servidor_apagado(self):
        self.app.bombear_comandos_remotos()
        self.girar(0.2)
        self.assertTrue(self.app.root.winfo_exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
