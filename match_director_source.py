"""
MATCH DE IMPRO - DIRECTOR (Versión 2.0)
------------------------------------------------------------------------------
Software de control para espectáculos de Match de Improvisación y competencias.
Gestiona cronómetro, puntajes, faltas, efectos de sonido y proyección multimedia.

Este archivo contiene el PANEL DEL OPERADOR. El resto vive en módulos aparte:
  · match_state.py    -> datos del partido, cronómetro y guardado en disco
  · tablero.py        -> motor de dibujo de la proyección
  · remote_control.py -> mando a distancia por WiFi (opcional)

Autor: Corporación Acción Impro
Ubicación: Medellín, Colombia
Año: 2026
Licencia: Creative Commons Atribución 4.0 Internacional (CC BY 4.0)
Usted es libre de compartir y adaptar este código siempre que reconozca la autoría.
------------------------------------------------------------------------------
"""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, font, messagebox, ttk

import pygame  # Librería para efectos de sonido

from match_state import (
    MAX_EQUIPOS, MAX_FALTAS, MIN_EQUIPOS, NUM_SONIDOS, TIEMPO_MAXIMO,
    EstadoPartido, cargar_json, guardar_json, ruta_config,
)
from tablero import CALIDAD_ALTA, CALIDAD_RAPIDA, Tablero

VERSION = "2.0"

# --- CONFIGURACIÓN DE AUDIO ---
# Intentamos iniciar el mixer. Si falla (ej. no hay tarjeta de sonido), el programa sigue funcionando sin audio.
AUDIO_ENABLED = False
try:
    pygame.mixer.init()
    # Más canales que ranuras: permite encadenar efectos sin que se corten entre sí.
    pygame.mixer.set_num_channels(16)
    AUDIO_ENABLED = True
except Exception:
    print("Advertencia: No se detectó dispositivo de audio. El modo sonido estará desactivado.")

# --- CONTROL REMOTO (opcional) ---
# Módulo propio, solo librería estándar. Si falta el archivo, la app sigue funcionando.
try:
    from remote_control import ControlRemoto, generar_pin
    REMOTE_ENABLED = True
except Exception:
    ControlRemoto = None
    generar_pin = None
    REMOTE_ENABLED = False
    print("Advertencia: No se encontró 'remote_control.py'. El mando a distancia estará desactivado.")

# --- RITMOS DE LOS BUCLES (ms) ---
REMOTE_POLL_MS = 120      # Revisión de comandos llegados del celular
TIMER_TICK_MS = 100       # Refresco del cronómetro (el reloj real es monotónico)
REFINAR_MS = 220          # Espera tras redimensionar para reescalar en alta calidad
AUTOGUARDADO_MS = 3000    # Espera tras el último cambio para guardar preferencias

# --- PALETA DEL PANEL ---
# Los grises de texto están elegidos para superar el contraste mínimo AA (4.5:1)
# sobre sus fondos: el panel se opera en salas a oscuras y los tonos de la v1
# (#666 sobre #333 daba 2.2:1) resultaban ilegibles.
FONDO = "#222222"
FONDO_FILA = "#333333"
ACENTO = "#00d4ff"
VERDE = "#1d7a4a"
ROJO = "#a32d2d"
COLOR_BOTON_FX = "#333333"

TEXTO = "#ffffff"           # 15.9:1 sobre el panel
TEXTO_SUAVE = "#c4c4c4"     #  9.2:1 sobre el panel
TEXTO_TENUE = "#a8a8a8"     #  6.7:1 sobre el panel · 5.3:1 sobre las filas
AVISO_OK = "#5fe08a"
AVISO_ALERTA = "#ffd166"
AVISO_ERROR = "#ff7b72"

# Vista previa del tablero dentro del panel
PREVIEW_ANCHO = 244


class ImproMatchApp:
    def __init__(self, iniciar_bucle=True):
        # Configuración de la Ventana Principal (Panel de Control)
        self.root = tk.Tk()
        self.root.title(f"Match Impro Director {VERSION} - Acción Impro 2026")
        self.root.geometry("560x980")
        self.root.minsize(480, 620)
        self.root.configure(bg=FONDO)

        # --- MODELO DE DATOS ---
        self.estado = EstadoPartido(num_equipos=3)

        # Preferencias guardadas de la función anterior (puede cambiar el número
        # de equipos, así que la variable del spinbox se crea después).
        self.ruta_preferencias = ruta_config()
        self.cargar_preferencias(silencioso=True)
        self.num_equipos_var = tk.IntVar(value=len(self.estado.equipos))

        # --- ESTADO DE LA INTERFAZ ---
        self.is_fullscreen = False
        self._redibujo_pendiente = False
        self._id_refinado = None
        self._id_autoguardado = None
        self._id_tic = None
        self._id_remoto = None
        self._ultimo_tamano = (0, 0)
        self._ultimo_segundo_pintado = None

        # Variables Tk espejo del diseño (se sincronizan en ambos sentidos)
        d = self.estado.diseno
        self.ver_timer = tk.BooleanVar(value=d.ver_timer)
        self.ver_faltas = tk.BooleanVar(value=d.ver_faltas)
        self.var_outline = tk.BooleanVar(value=d.ver_outline)
        self.ver_barra_color = tk.BooleanVar(value=d.ver_barra_color)

        # --- CONTROL REMOTO ---
        self.remoto = None
        self.remote_port_var = tk.StringVar(value="8770")
        self.remote_pin_var = tk.StringVar(value="------")
        self.remote_url_var = tk.StringVar(value="Servidor apagado")
        self.estado_var = tk.StringVar(value="Listo.")

        # --- VENTANA DEL PROYECTOR ---
        self.crear_ventana_proyector()

        # --- INTERFAZ DEL OPERADOR ---
        self.construir_panel_control()
        self.registrar_atajos()
        self.recargar_sonidos_guardados()
        self.redibujar_ahora()

        # Cierre ordenado y bucles permanentes
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_app)
        self._id_remoto = self.root.after(REMOTE_POLL_MS, self.bombear_comandos_remotos)
        self._id_tic = self.root.after(TIMER_TICK_MS, self.tic_cronometro)

        if iniciar_bucle:
            self.root.mainloop()

    # ==========================================================================
    # VENTANAS
    # ==========================================================================
    def crear_ventana_proyector(self):
        """Ventana negra que se arrastra al proyector o a la segunda pantalla."""
        self.win_proj = tk.Toplevel(self.root)
        self.win_proj.title("Tablero Público (Proyector)")
        self.win_proj.geometry("800x450")
        self.win_proj.configure(bg="black")
        # Cerrar el tablero por error dejaría el show sin marcador: lo reabrimos.
        self.win_proj.protocol("WM_DELETE_WINDOW", self.cerrar_app)

        self.canvas = tk.Canvas(self.win_proj, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.tablero = Tablero(self.canvas)

        # Doble clic solo en el lienzo para evitar conflictos
        self.canvas.bind("<Double-Button-1>", self.alternar_pantalla_completa)
        self.win_proj.bind("<Configure>", self.al_redimensionar)

    # ==========================================================================
    # PANEL DE CONTROL
    # ==========================================================================
    def construir_panel_control(self):
        """Construye la barra superior, las pestañas y la barra de estado."""
        self.construir_barra_superior()

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        tab_vivo = tk.Frame(nb, bg=FONDO); nb.add(tab_vivo, text="🔴 EN VIVO")
        self.construir_tab_en_vivo(tab_vivo)

        tab_diseno = tk.Frame(nb, bg=FONDO); nb.add(tab_diseno, text="🎨 DISEÑO")
        self.construir_tab_diseno(tab_diseno)

        tab_fx = tk.Frame(nb, bg=FONDO); nb.add(tab_fx, text="⚙ SONIDOS")
        self.construir_tab_sonidos(tab_fx)

        tab_remoto = tk.Frame(nb, bg=FONDO); nb.add(tab_remoto, text="📡 REMOTO")
        self.construir_tab_remoto(tab_remoto)

        tab_ayuda = tk.Frame(nb, bg=FONDO); nb.add(tab_ayuda, text="❔ AYUDA")
        self.construir_tab_ayuda(tab_ayuda)

        # Barra de estado inferior: es el único canal de aviso del programa,
        # así que va con tamaño legible y color según la importancia.
        self.lbl_estado = tk.Label(self.root, textvariable=self.estado_var, bg="#1a1a1a",
                                   fg=TEXTO_TENUE, anchor="w", font=("Arial", 9),
                                   padx=8, pady=3)
        self.lbl_estado.pack(fill="x", side="bottom")

    def construir_barra_superior(self):
        """Acciones siempre a mano: presets, deshacer y pantalla completa."""
        barra = tk.Frame(self.root, bg="#1a1a1a")
        barra.pack(fill="x", padx=5, pady=5)

        def boton(texto, comando, color=FONDO_FILA, lado="left"):
            b = tk.Button(barra, text=texto, command=comando, bg=color, fg=TEXTO,
                          font=("Arial", 8, "bold"), bd=0, padx=7, pady=5,
                          activebackground="#4a4a4a")
            b.pack(side=lado, padx=2)
            return b

        def separador():
            tk.Frame(barra, bg="#3a3a3a", width=1).pack(side="left", fill="y",
                                                        padx=6, pady=3)

        # Acciones frecuentes de la función
        self.btn_deshacer = boton("↩ Deshacer", self.deshacer)
        self.btn_rehacer = boton("↪ Rehacer", self.rehacer)
        separador()
        boton("💾 Guardar", self.guardar_preset_como)
        boton("📂 Cargar", self.cargar_preset_desde)

        # Pantalla completa a la derecha, y la acción destructiva al extremo
        # opuesto de Deshacer para que un clic errado no borre el marcador.
        boton("⛶ Pantalla completa", self.alternar_pantalla_completa,
              ACENTO, lado="right").config(fg="black")
        boton("🧹 Reiniciar", self.reiniciar_marcador, "#5a3030", lado="right")
        self.actualizar_botones_historial()

    # --- PESTAÑA: EN VIVO ---------------------------------------------------
    def construir_tab_en_vivo(self, parent):
        # Fila superior: vista previa + cronómetro, lado a lado para ahorrar alto
        fila_sup = tk.Frame(parent, bg=FONDO)
        fila_sup.pack(fill="x", padx=10, pady=5)

        self.construir_vista_previa(fila_sup)

        fr_t = tk.LabelFrame(fila_sup, text="CRONÓMETRO", font=("Arial", 10, "bold"),
                             bg=FONDO, fg=TEXTO)
        fr_t.pack(side="left", fill="both", expand=True)

        # Reloj grande: el operador no debería tener que mirar el proyector.
        self.lbl_reloj = tk.Label(fr_t, text=self.estado.cronometro.texto(), bg=FONDO,
                                  fg=ACENTO, font=("Consolas", 30, "bold"))
        self.lbl_reloj.pack(pady=(4, 0))

        f_in = tk.Frame(fr_t, bg=FONDO); f_in.pack(pady=2)
        self.e_min = tk.Entry(f_in, width=3, font=("Arial", 13), justify="center")
        self.e_sec = tk.Entry(f_in, width=3, font=("Arial", 13), justify="center")
        duracion = self.estado.cronometro.duracion
        self.e_min.insert(0, str(duracion // 60))
        self.e_sec.insert(0, f"{duracion % 60:02d}")
        self.e_min.pack(side="left")
        tk.Label(f_in, text=":", bg=FONDO, fg=TEXTO).pack(side="left")
        self.e_sec.pack(side="left")
        tk.Button(f_in, text="SET", command=self.set_tiempo, width=4,
                  font=("Arial", 8, "bold")).pack(side="left", padx=6)

        f_btn = tk.Frame(fr_t, bg=FONDO); f_btn.pack(pady=4)
        tk.Button(f_btn, text="▶ INICIO", bg="#afa", width=9, height=2,
                  font=("Arial", 9, "bold"),
                  command=self.iniciar_tiempo).pack(side="left", padx=3)
        tk.Button(f_btn, text="⏸ PAUSA", bg="#fea", width=9, height=2,
                  font=("Arial", 9, "bold"),
                  command=self.pausar_tiempo).pack(side="left", padx=3)

        f_aj = tk.Frame(fr_t, bg=FONDO); f_aj.pack(pady=(0, 6))
        for etiqueta, delta in (("−30s", -30), ("−10s", -10), ("+10s", 10), ("+30s", 30)):
            tk.Button(f_aj, text=etiqueta, width=4, bg=FONDO_FILA, fg=TEXTO,
                      font=("Arial", 8), command=lambda d=delta: self.ajustar_tiempo(d)
                      ).pack(side="left", padx=2)

        # Número de equipos
        fr_cfg = tk.Frame(parent, bg=FONDO); fr_cfg.pack(fill="x", padx=10)
        tk.Label(fr_cfg, text="Equipos:", fg=TEXTO_SUAVE, bg=FONDO).pack(side="left")
        tk.Spinbox(fr_cfg, from_=MIN_EQUIPOS, to=MAX_EQUIPOS, textvariable=self.num_equipos_var,
                   width=3, state="readonly",
                   command=self.actualizar_estructura_equipos).pack(side="left", padx=5)
        tk.Label(fr_cfg, text=f"(máx. {MAX_FALTAS} faltas por equipo)", fg=TEXTO_TENUE,
                 bg=FONDO, font=("Arial", 8)).pack(side="left")

        # Tiras de equipos
        self.frame_container_eq = tk.Frame(parent, bg=FONDO)
        self.frame_container_eq.pack(fill="both", expand=True, padx=5, pady=5)
        self.dibujar_tiras_equipos()

        # Soundbar
        fr_snd = tk.LabelFrame(parent, text="EFECTOS", bg=FONDO, fg=ACENTO,
                               font=("Arial", 10, "bold"))
        fr_snd.pack(fill="x", padx=10, pady=10, side="bottom")

        self.botones_sonido_live = []
        rejilla = tk.Frame(fr_snd, bg=FONDO); rejilla.pack(fill="x")
        for i in range(NUM_SONIDOS):
            btn = tk.Button(rejilla, text=self.estado.sonidos[i].nombre, bg=COLOR_BOTON_FX,
                            fg="white", font=("Arial", 9, "bold"), height=2,
                            command=lambda x=i: self.play_sound(x))
            btn.grid(row=0 if i < 3 else 1, column=i % 3, sticky="nsew", padx=2, pady=2)
            rejilla.grid_columnconfigure(i % 3, weight=1)
            self.botones_sonido_live.append(btn)

        f_vol = tk.Frame(fr_snd, bg=FONDO); f_vol.pack(fill="x", pady=(4, 2))
        tk.Label(f_vol, text="Volumen", bg=FONDO, fg=TEXTO_SUAVE, font=("Arial", 8)).pack(side="left")
        self.scale_volumen = tk.Scale(f_vol, from_=0, to=100, orient="horizontal", bg=FONDO,
                                      fg="white", highlightthickness=0, bd=0, showvalue=False,
                                      command=self.cambiar_volumen)
        self.scale_volumen.set(int(self.estado.volumen * 100))
        self.scale_volumen.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(f_vol, text="⏹ Silenciar", bg=FONDO_FILA, fg="white", font=("Arial", 8),
                  command=self.detener_sonidos).pack(side="right")


    def construir_vista_previa(self, parent):
        """
        Miniatura en vivo de lo que está viendo el público.

        Una vez el tablero está a pantalla completa en el proyector, el operador
        deja de verlo: normalmente está de espaldas a la pantalla. Esta vista
        evita tener que girarse para comprobar qué se está proyectando.
        """
        self.marco_preview = tk.LabelFrame(parent, text="LO QUE VE EL PÚBLICO",
                                           font=("Arial", 8, "bold"), bg=FONDO,
                                           fg=TEXTO_TENUE)
        self.marco_preview.pack(side="left", fill="y", padx=(0, 8))

        self.canvas_preview = tk.Canvas(self.marco_preview, bg="black",
                                        width=PREVIEW_ANCHO,
                                        height=int(PREVIEW_ANCHO * 9 / 16),
                                        highlightthickness=1,
                                        highlightbackground="#444")
        self.canvas_preview.pack(padx=4, pady=(2, 4))
        self.tablero_preview = Tablero(self.canvas_preview)
        # Un clic en la miniatura lleva el tablero real a pantalla completa.
        self.canvas_preview.bind("<Button-1>", self.alternar_pantalla_completa)

        self.ver_preview = tk.BooleanVar(value=True)
        tk.Checkbutton(self.marco_preview, text="Mostrar", variable=self.ver_preview,
                       bg=FONDO, fg=TEXTO_TENUE, selectcolor="#444", font=("Arial", 7),
                       activebackground=FONDO, activeforeground=TEXTO,
                       command=self.alternar_vista_previa).pack(pady=(0, 2))

    def dibujar_tiras_equipos(self):
        """Dibuja los controles de cada equipo en la pestaña EN VIVO."""
        for widget in self.frame_container_eq.winfo_children():
            widget.destroy()
        self.lbls_puntos_ctrl = []
        self.entries_nombres = []
        self.botones_color = []
        self.luces_faltas = []

        for i, equipo in enumerate(self.estado.equipos):
            fr = tk.Frame(self.frame_container_eq, bg=FONDO_FILA, pady=4)
            fr.pack(fill="x", pady=2)

            f_top = tk.Frame(fr, bg=FONDO_FILA); f_top.pack(fill="x", padx=5)
            tk.Label(f_top, text=f"{i + 1}", bg=FONDO_FILA, fg=TEXTO_TENUE,
                     font=("Arial", 8, "bold"), width=2).pack(side="left")

            btn_color = tk.Button(f_top, bg=equipo.color, width=2, bd=0,
                                  activebackground=equipo.color,
                                  command=lambda x=i: self.elegir_color_equipo(x))
            btn_color.pack(side="left", padx=(0, 4))
            self.botones_color.append(btn_color)

            en = tk.Entry(f_top, bg=FONDO, fg=TEXTO, font=("Arial", 11, "bold"),
                          justify="center", insertbackground=TEXTO)
            en.insert(0, equipo.nombre)
            en.pack(side="left", fill="x", expand=True)
            en.bind("<KeyRelease>", lambda e, idx=i: self.actualizar_nombre_live(idx))
            self.entries_nombres.append(en)

            f_ctrl = tk.Frame(fr, bg=FONDO_FILA); f_ctrl.pack(fill="x", padx=5, pady=(5, 0))

            # Puntos: es la acción más repetida de la noche, así que es la que
            # más área táctil recibe.
            tk.Button(f_ctrl, text="−", width=3, height=2, bg="#4a4a4a", fg=TEXTO,
                      font=("Arial", 12, "bold"), activebackground="#5c5c5c",
                      command=lambda x=i: self.mod(x, -1, 'p')).pack(side="left")
            lbl = tk.Label(f_ctrl, text=str(equipo.puntos), font=("Impact", 22), width=3,
                           bg=FONDO_FILA, fg=ACENTO)
            lbl.pack(side="left", padx=4)
            self.lbls_puntos_ctrl.append(lbl)
            tk.Button(f_ctrl, text="+", width=3, height=2, bg="#4a4a4a", fg=TEXTO,
                      font=("Arial", 12, "bold"), activebackground="#5c5c5c",
                      command=lambda x=i: self.mod(x, 1, 'p')).pack(side="left")

            # Semáforo de faltas: antes solo existía en el proyector, así que el
            # operador tenía que girarse para saber cuántas llevaba cada equipo.
            f_faltas = tk.Frame(f_ctrl, bg=FONDO_FILA)
            f_faltas.pack(side="left", padx=10)
            luces = []
            for _ in range(MAX_FALTAS):
                punto = tk.Label(f_faltas, text="●", bg=FONDO_FILA, fg=TEXTO_TENUE,
                                 font=("Arial", 15))
                punto.pack(side="left", padx=1)
                luces.append(punto)
            self.luces_faltas.append(luces)

            tk.Button(f_ctrl, text="FALTA", bg="#d44", fg=TEXTO, font=("Arial", 8, "bold"),
                      height=2, width=6, activebackground="#e65a5a",
                      command=lambda x=i: self.mod(x, 1, 'f')).pack(side="right")
            tk.Button(f_ctrl, text="quitar", bg="#4a4a4a", fg=TEXTO_TENUE,
                      font=("Arial", 7), height=2,
                      command=lambda x=i: self.mod(x, -1, 'f')).pack(side="right", padx=3)

        self.refrescar_luces_faltas()

    # --- PESTAÑA: DISEÑO ----------------------------------------------------
    def construir_tab_diseno(self, parent):
        d = self.estado.diseno
        self.sliders_diseno = {}
        lienzo, contenido = self.crear_area_con_scroll(parent)

        # Imágenes
        fr_img = tk.LabelFrame(contenido, text="Imágenes (Fondo y Logo)", bg=FONDO, fg="white")
        fr_img.pack(fill="x", padx=10, pady=5)

        f_fondo = tk.Frame(fr_img, bg=FONDO); f_fondo.pack(fill="x", pady=2)
        tk.Button(f_fondo, text="🖼 Cambiar Fondo", command=self.cambiar_fondo,
                  bg="#444", fg="white").pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(f_fondo, text="❌", command=self.quitar_fondo, bg="#522",
                  fg="white").pack(side="left", padx=5)

        f_logo = tk.Frame(fr_img, bg=FONDO); f_logo.pack(fill="x", pady=2)
        tk.Button(f_logo, text="⭐ Cargar Logo", command=self.cambiar_logo,
                  bg="#444", fg="white").pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(f_logo, text="❌", command=self.quitar_logo, bg="#522",
                  fg="white").pack(side="left", padx=5)

        self.mk_slider(fr_img, "Tam. Logo", 0.1, 2.0, 0.05, 'logo_scale')
        self.mk_slider(fr_img, "Pos. Y Logo", -0.5, 0.5, 0.01, 'logo_offset_y')

        # Visibilidad
        fr_vis = tk.LabelFrame(contenido, text="Visibilidad", bg=FONDO, fg="#00ff88")
        fr_vis.pack(fill="x", padx=10, pady=5)
        for texto, var, attr in (("Timer", self.ver_timer, 'ver_timer'),
                                 ("Faltas", self.ver_faltas, 'ver_faltas'),
                                 ("Outline", self.var_outline, 'ver_outline'),
                                 ("Barra color", self.ver_barra_color, 'ver_barra_color')):
            tk.Checkbutton(fr_vis, text=texto, variable=var, bg=FONDO, fg="white",
                           selectcolor="#444", activebackground=FONDO, font=("Arial", 8),
                           command=lambda v=var, a=attr: self.cambiar_visibilidad(a, v)
                           ).pack(side="left", padx=6)

        # Colores
        fr_col = tk.LabelFrame(contenido, text="Colores", bg=FONDO, fg="white")
        fr_col.pack(fill="x", padx=10, pady=5)
        self.botones_color_diseno = {}
        for etiqueta, attr in (("Nombres", 'color_nombres'), ("Puntos", 'color_puntos'),
                               ("Faltas", 'color_faltas'), ("Cajas", 'color_caja'),
                               ("Reloj", 'color_timer'), ("Alerta", 'color_alerta')):
            b = tk.Button(fr_col, text=etiqueta, bg=getattr(d, attr), font=("Arial", 8),
                          command=lambda a=attr: self.elegir_color_diseno(a))
            b.pack(side="left", expand=True, fill="x", padx=1)
            self.botones_color_diseno[attr] = b

        # Geometría
        fr_lay = tk.LabelFrame(contenido, text="Geometría", bg=FONDO, fg="white")
        fr_lay.pack(fill="x", padx=10, pady=5)

        f_tim = tk.Frame(fr_lay, bg=FONDO); f_tim.pack(fill="x", padx=5, pady=5)
        tk.Label(f_tim, text="Base Timer:", bg=FONDO, fg=TEXTO_SUAVE).pack(side="left")
        self.combo_timer = ttk.Combobox(f_tim, values=["Arriba", "Abajo"],
                                        state="readonly", width=8)
        self.combo_timer.set(d.timer_position)
        self.combo_timer.pack(side="left", padx=5)
        self.combo_timer.bind("<<ComboboxSelected>>", self.cambiar_pos_timer)

        tk.Label(f_tim, text="Alerta (s):", bg=FONDO, fg=TEXTO_SUAVE).pack(side="left", padx=(10, 2))
        # Con textvariable: un Spinbox en 'readonly' ignora delete()/insert(),
        # así que la variable es la única forma fiable de fijarlo por código.
        self.var_alerta = tk.StringVar(value=str(d.segundos_alerta))
        self.spin_alerta = tk.Spinbox(f_tim, from_=0, to=60, width=4, state="readonly",
                                      textvariable=self.var_alerta,
                                      command=self.cambiar_segundos_alerta)
        self.spin_alerta.pack(side="left")

        self.mk_slider(fr_lay, "Pos. Vertical (Todo)", -0.5, 0.5, 0.01, 'offset_global_y')
        self.mk_slider(fr_lay, "Pos. Horizontal", -0.3, 0.3, 0.01, 'offset_x')
        self.mk_slider(fr_lay, "Offset Nombres", -0.2, 0.2, 0.01, 'offset_names')
        self.mk_slider(fr_lay, "Offset Puntos", -0.2, 0.2, 0.01, 'offset_scores')
        self.mk_slider(fr_lay, "Ajuste Timer", -0.5, 0.5, 0.01, 'offset_timer')
        tk.Label(fr_lay, text="--- GENERAL ---", bg=FONDO, fg=TEXTO_TENUE,
                 font=("Arial", 7)).pack(pady=2)
        self.mk_slider(fr_lay, "Tam. Nombres", 0.5, 3.0, 0.1, 'name_scale')
        self.mk_slider(fr_lay, "Zoom General", 0.5, 2.0, 0.05, 'scale_factor')
        self.mk_slider(fr_lay, "Margen Cajas", 0.5, 2.0, 0.05, 'box_padding')
        self.mk_slider(fr_lay, "Redondez Cajas", 0, 60, 1, 'corner_radius')

        # Fuentes
        fr_f = tk.LabelFrame(contenido, text="Fuentes", bg=FONDO, fg="white")
        fr_f.pack(fill="x", padx=10, pady=5)
        familias = sorted({f for f in font.families() if not f.startswith("@")})

        tk.Label(fr_f, text="Nombres", bg=FONDO, fg=TEXTO_SUAVE, font=("Arial", 8),
                 anchor="w").pack(fill="x", padx=5)
        cb_nombres = ttk.Combobox(fr_f, values=familias, state="readonly")
        cb_nombres.set(d.font_family)
        cb_nombres.pack(fill="x", padx=5, pady=2)
        cb_nombres.bind("<<ComboboxSelected>>",
                        lambda e: self.set_font(cb_nombres.get(), 'names'))
        self.combo_font_nombres = cb_nombres

        tk.Label(fr_f, text="Puntos y reloj", bg=FONDO, fg=TEXTO_SUAVE, font=("Arial", 8),
                 anchor="w").pack(fill="x", padx=5)
        cb_score = ttk.Combobox(fr_f, values=familias, state="readonly")
        cb_score.set(d.font_score)
        cb_score.pack(fill="x", padx=5, pady=2)
        cb_score.bind("<<ComboboxSelected>>",
                      lambda e: self.set_font(cb_score.get(), 'score'))
        self.combo_font_score = cb_score

        tk.Button(contenido, text="♻ Restablecer diseño por defecto", bg="#444", fg="white",
                  font=("Arial", 8), command=self.restablecer_diseno).pack(fill="x", padx=10,
                                                                           pady=(5, 15))
        self._lienzo_diseno = lienzo

    def crear_area_con_scroll(self, parent):
        """
        La pestaña de diseño tiene más controles que alto de ventana.
        Este contenedor permite desplazarla con la rueda del ratón.
        """
        lienzo = tk.Canvas(parent, bg=FONDO, highlightthickness=0)
        barra = ttk.Scrollbar(parent, orient="vertical", command=lienzo.yview)
        contenido = tk.Frame(lienzo, bg=FONDO)

        ventana = lienzo.create_window((0, 0), window=contenido, anchor="nw")
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        contenido.bind("<Configure>",
                       lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(ventana, width=e.width))

        def rueda(evento):
            paso = -1 if getattr(evento, "delta", 0) > 0 or evento.num == 4 else 1
            lienzo.yview_scroll(paso, "units")

        for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            lienzo.bind_all(secuencia, rueda, add="+")
        return lienzo, contenido

    def mk_slider(self, padre, texto, vmin, vmax, resolucion, attr):
        f = tk.Frame(padre, bg=FONDO); f.pack(fill="x", pady=1)
        tk.Label(f, text=texto, bg=FONDO, fg=TEXTO_SUAVE, width=20, anchor="w",
                 font=("Arial", 8)).pack(side="left")
        s = tk.Scale(f, from_=vmin, to=vmax, resolution=resolucion, orient="horizontal",
                     bg=FONDO, fg="white", highlightthickness=0, bd=0,
                     command=lambda v, a=attr: self.upd_lay(a, v))
        s.set(getattr(self.estado.diseno, attr))
        s.pack(side="right", fill="x", expand=True)
        # Guardamos la referencia para poder resincronizarlo al cargar un preset.
        self.sliders_diseno[attr] = s
        return s

    # --- PESTAÑA: SONIDOS ---------------------------------------------------
    def construir_tab_sonidos(self, parent):
        tk.Label(parent, text=f"CONFIGURAR BOTONES ({NUM_SONIDOS} SLOTS)", bg=FONDO,
                 fg=ACENTO, font=("Arial", 12, "bold")).pack(pady=10)
        if not AUDIO_ENABLED:
            tk.Label(parent, text="⚠ No se detectó dispositivo de audio en este equipo.",
                     bg=FONDO, fg="#ff8888", font=("Arial", 9)).pack(pady=(0, 10))

        self.lbls_estado_sonido = []
        self.entries_sonido = []
        for i in range(NUM_SONIDOS):
            fila = tk.Frame(parent, bg=FONDO_FILA, pady=5)
            fila.pack(fill="x", padx=10, pady=2)
            tk.Label(fila, text=f"#{i + 1}", bg=FONDO_FILA, fg=TEXTO_TENUE, width=3).pack(side="left")

            entrada = tk.Entry(fila, width=14)
            entrada.insert(0, self.estado.sonidos[i].nombre)
            entrada.pack(side="left", padx=5)
            entrada.bind("<KeyRelease>",
                         lambda e, idx=i, w=entrada: self.update_sound_name(idx, w.get()))
            self.entries_sonido.append(entrada)

            tk.Button(fila, text="📂", command=lambda x=i: self.cargar_sonido(x)).pack(side="left")
            tk.Button(fila, text="✖", font=("Arial", 7), bg="#522", fg="white",
                      command=lambda x=i: self.vaciar_sonido(x)).pack(side="left", padx=2)

            etiqueta = tk.Label(fila, text="Vacío", bg=FONDO_FILA, fg=TEXTO_TENUE, width=16,
                                anchor="w", font=("Arial", 8))
            etiqueta.pack(side="left", padx=5)
            self.lbls_estado_sonido.append(etiqueta)

            tk.Button(fila, text="▶", command=lambda x=i: self.play_sound(x), bg="#444",
                      fg="white").pack(side="right", padx=5)

        tk.Label(parent, bg=FONDO, fg=TEXTO_TENUE, font=("Arial", 8), justify="left", anchor="w",
                 text=("Formatos: MP3, WAV y OGG.\n"
                       "Las rutas quedan guardadas: al reabrir el programa los efectos\n"
                       "se recargan solos, siempre que los archivos sigan en su sitio.")
                 ).pack(fill="x", padx=15, pady=10)

    # --- PESTAÑA: REMOTO ----------------------------------------------------
    def construir_tab_remoto(self, parent):
        tk.Label(parent, text="MANDO A DISTANCIA (WiFi)", bg=FONDO, fg=ACENTO,
                 font=("Arial", 12, "bold")).pack(pady=(10, 2))
        tk.Label(parent, text="Controla puntos, faltas, cronómetro y efectos\ndesde tu celular o tablet.",
                 bg=FONDO, fg=TEXTO_SUAVE, font=("Arial", 9), justify="center").pack(pady=(0, 10))

        if not REMOTE_ENABLED:
            tk.Label(parent, text="⚠ Falta el archivo 'remote_control.py'.\nDescárgalo junto al programa para usar esta función.",
                     bg=FONDO, fg="#ff8888", font=("Arial", 9), justify="center").pack(pady=20)
            return

        fr_cfg = tk.LabelFrame(parent, text="Servidor", bg=FONDO, fg="white")
        fr_cfg.pack(fill="x", padx=10, pady=5)
        f_port = tk.Frame(fr_cfg, bg=FONDO); f_port.pack(fill="x", padx=5, pady=5)
        tk.Label(f_port, text="Puerto:", bg=FONDO, fg=TEXTO_SUAVE).pack(side="left")
        self.entry_puerto = tk.Entry(f_port, textvariable=self.remote_port_var, width=6,
                                     justify="center")
        self.entry_puerto.pack(side="left", padx=5)
        self.btn_remoto = tk.Button(f_port, text="▶ ENCENDER", bg=VERDE, fg="white",
                                    font=("Arial", 9, "bold"), command=self.alternar_remoto)
        self.btn_remoto.pack(side="right", padx=5)

        fr_conn = tk.LabelFrame(parent, text="Datos de conexión", bg=FONDO, fg="#00ff88")
        fr_conn.pack(fill="x", padx=10, pady=5)
        tk.Label(fr_conn, text="Dirección (escríbela en el navegador del celular):",
                 bg=FONDO, fg=TEXTO_SUAVE, font=("Arial", 8)).pack(anchor="w", padx=5, pady=(5, 0))
        self.lbl_url = tk.Entry(fr_conn, textvariable=self.remote_url_var, state="readonly",
                                readonlybackground="#111", fg=ACENTO, justify="center",
                                font=("Consolas", 12, "bold"), bd=0)
        self.lbl_url.pack(fill="x", padx=5, pady=3)

        f_pin = tk.Frame(fr_conn, bg=FONDO); f_pin.pack(fill="x", padx=5, pady=5)
        tk.Label(f_pin, text="PIN:", bg=FONDO, fg=TEXTO_SUAVE).pack(side="left")
        tk.Label(f_pin, textvariable=self.remote_pin_var, bg=FONDO, fg="#ffcc00",
                 font=("Consolas", 18, "bold")).pack(side="left", padx=8)
        tk.Button(f_pin, text="🔄 Nuevo PIN", bg="#444", fg="white", font=("Arial", 8),
                  command=self.regenerar_pin).pack(side="right")

        tk.Label(parent, justify="left", bg=FONDO, fg=TEXTO_TENUE, font=("Arial", 8), anchor="w",
                 text=("CÓMO USARLO\n"
                       "1. Conecta el computador y el celular a la MISMA red WiFi.\n"
                       "2. Presiona ENCENDER y escribe la dirección en el navegador del celular.\n"
                       "3. Ingresa el PIN una sola vez; el celular lo recuerda.\n\n"
                       "SEGURIDAD\n"
                       "· Cualquiera en esa red puede llegar al mando, por eso existe el PIN.\n"
                       "· En redes públicas genera un PIN nuevo antes de la función.\n"
                       "· Apaga el servidor al terminar el show.\n"
                       "· Si Windows pregunta por el Firewall, permite el acceso en red privada.")
                 ).pack(fill="x", padx=15, pady=10)

    # --- PESTAÑA: AYUDA -----------------------------------------------------
    def construir_tab_ayuda(self, parent):
        tk.Label(parent, text=f"MATCH IMPRO DIRECTOR {VERSION}", bg=FONDO, fg=ACENTO,
                 font=("Arial", 13, "bold")).pack(pady=(12, 2))
        tk.Label(parent, text="Corporación Acción Impro · Medellín, Colombia",
                 bg=FONDO, fg=TEXTO_SUAVE, font=("Arial", 9)).pack()

        fr = tk.LabelFrame(parent, text="Atajos de teclado", bg=FONDO, fg="white")
        fr.pack(fill="x", padx=12, pady=12)
        atajos = [
            ("Espacio", "Inicia o pausa el cronómetro"),
            ("1 … 6", "Suma un punto al equipo N"),
            ("Shift + 1 … 6", "Resta un punto al equipo N"),
            ("F1 … F6", "Marca una falta al equipo N"),
            ("Ctrl + Z / Ctrl + Y", "Deshacer / rehacer una jugada"),
            ("Ctrl + S", "Guardar las preferencias ahora"),
            ("Ctrl + R", "Reiniciar el marcador"),
            ("F11 o doble clic", "Pantalla completa del tablero"),
            ("Esc", "Salir de pantalla completa"),
        ]
        for tecla, accion in atajos:
            fila = tk.Frame(fr, bg=FONDO); fila.pack(fill="x", padx=8, pady=1)
            tk.Label(fila, text=tecla, bg=FONDO, fg="#ffcc00", font=("Consolas", 9, "bold"),
                     width=18, anchor="w").pack(side="left")
            tk.Label(fila, text=accion, bg=FONDO, fg=TEXTO_SUAVE, font=("Arial", 8),
                     anchor="w").pack(side="left")
        tk.Label(fr, text="Los atajos se ignoran mientras escribes en una casilla de texto.",
                 bg=FONDO, fg=TEXTO_TENUE, font=("Arial", 7), anchor="w").pack(fill="x", padx=8,
                                                                          pady=(6, 6))

        fr2 = tk.LabelFrame(parent, text="Preferencias", bg=FONDO, fg="white")
        fr2.pack(fill="x", padx=12, pady=(0, 12))
        tk.Label(fr2, bg=FONDO, fg=TEXTO_TENUE, font=("Arial", 8), justify="left", anchor="w",
                 text=("El diseño, los nombres de equipo, los colores y las rutas de los\n"
                       "efectos se guardan solos y se recuperan al abrir el programa.\n"
                       "Con 💾 Guardar puedes exportar un preset por espectáculo.")
                 ).pack(fill="x", padx=8, pady=6)
        tk.Label(fr2, text=f"Archivo: {self.ruta_preferencias}", bg=FONDO, fg=TEXTO_TENUE,
                 font=("Arial", 7), anchor="w", wraplength=500,
                 justify="left").pack(fill="x", padx=8, pady=(0, 8))

        tk.Label(parent, bg=FONDO, fg=TEXTO_TENUE, font=("Arial", 8), justify="center",
                 text="Licencia Creative Commons CC BY 4.0\nHecho por y para improvisadores 🎭"
                 ).pack(side="bottom", pady=12)

    # ==========================================================================
    # REDIBUJADO (COALESCIDO)
    # ==========================================================================
    def solicitar_redibujado(self):
        """
        Marca el tablero como sucio y lo redibuja una sola vez cuando Tk quede
        libre. Así, mover un slider o aplicar diez comandos remotos seguidos
        produce un único repintado en lugar de diez.
        """
        if self._redibujo_pendiente:
            return
        self._redibujo_pendiente = True
        self.root.after_idle(self._ejecutar_redibujado)

    def _ejecutar_redibujado(self):
        self._redibujo_pendiente = False
        self.redibujar_ahora()

    def redibujar_ahora(self, calidad=CALIDAD_ALTA):
        if not self.win_proj.winfo_exists():
            return
        ancho = self.win_proj.winfo_width()
        alto = self.win_proj.winfo_height()
        self._ultimo_tamano = (ancho, alto)
        self.tablero.dibujar(self.estado, ancho, alto, calidad)
        self.dibujar_vista_previa(ancho, alto)
        self._ultimo_segundo_pintado = self.estado.cronometro.restante

    def dibujar_vista_previa(self, ancho_real=None, alto_real=None):
        """Repinta la miniatura respetando la proporción del proyector."""
        if not self.ver_preview.get() or not self.canvas_preview.winfo_exists():
            return
        if ancho_real is None:
            ancho_real, alto_real = self._ultimo_tamano
        if ancho_real < 10 or alto_real < 10:
            return

        alto_mini = max(60, int(PREVIEW_ANCHO * alto_real / ancho_real))
        if int(self.canvas_preview.cget("height")) != alto_mini:
            self.canvas_preview.config(height=alto_mini)
        # Filtro rápido siempre: a este tamaño la diferencia no se aprecia y
        # evita duplicar el coste del redibujado del tablero real.
        self.tablero_preview.dibujar(self.estado, PREVIEW_ANCHO, alto_mini, CALIDAD_RAPIDA)

    def alternar_vista_previa(self):
        """Muestra u oculta la miniatura (útil en equipos muy justos de CPU)."""
        if self.ver_preview.get():
            self.canvas_preview.pack(padx=4, pady=(2, 4), before=self.marco_preview.winfo_children()[-1])
            self.dibujar_vista_previa()
        else:
            self.canvas_preview.pack_forget()

    def al_redimensionar(self, event=None):
        """
        Durante el arrastre llegan decenas de eventos <Configure>. Redibujamos
        con filtro rápido y programamos un refinado en alta calidad al soltar.
        """
        ancho = self.win_proj.winfo_width()
        alto = self.win_proj.winfo_height()
        if (ancho, alto) == self._ultimo_tamano:
            return  # Un <Configure> por movimiento de ventana, no por tamaño.

        self.redibujar_ahora(CALIDAD_RAPIDA)
        if self._id_refinado is not None:
            self.root.after_cancel(self._id_refinado)
        self._id_refinado = self.root.after(REFINAR_MS, self._refinar)

    def _refinar(self):
        self._id_refinado = None
        self.redibujar_ahora(CALIDAD_ALTA)

    # ==========================================================================
    # CRONÓMETRO
    # ==========================================================================
    def tic_cronometro(self):
        """
        Bucle ligero: solo toca la pantalla cuando cambia el segundo mostrado.
        El valor sale de un reloj monotónico, así que no acumula retraso.
        """
        crono = self.estado.cronometro
        if crono.revisar_agotado():
            self.avisar("⏰ ¡TIEMPO! Se acabó la cuenta regresiva.", 'alerta')
        segundo = crono.restante
        if segundo != self._ultimo_segundo_pintado:
            self._ultimo_segundo_pintado = segundo
            if not self.tablero.actualizar_timer(self.estado):
                self.solicitar_redibujado()
            if self.ver_preview.get():
                self.tablero_preview.actualizar_timer(self.estado)
            self.actualizar_reloj_panel()
        self._id_tic = self.root.after(TIMER_TICK_MS, self.tic_cronometro)

    def actualizar_reloj_panel(self):
        """Refresca el reloj grande del panel del operador."""
        try:
            if self.lbl_reloj.winfo_exists():
                segundo = self.estado.cronometro.restante
                self.lbl_reloj.config(
                    text=self.estado.cronometro.texto(),
                    fg="#ff5555" if segundo <= self.estado.diseno.segundos_alerta else ACENTO)
        except (AttributeError, tk.TclError):
            pass

    def set_tiempo(self):
        """Lee las casillas de minutos y segundos y fija el cronómetro."""
        try:
            minutos = int(self.e_min.get() or 0)
            segundos = int(self.e_sec.get() or 0)
        except ValueError:
            self.avisar("Minutos y segundos deben ser números.", 'error')
            return
        if minutos < 0 or segundos < 0 or segundos > 59:
            self.avisar("Revisa el tiempo: los segundos van de 0 a 59.", 'error')
            return
        total = min(minutos * 60 + segundos, TIEMPO_MAXIMO)
        self.estado.cronometro.fijar(total)
        self.sincronizar_casillas_tiempo()
        self.forzar_refresco_reloj()
        self.programar_autoguardado()

    def ajustar_tiempo(self, delta):
        self.estado.cronometro.ajustar(delta)
        self.sincronizar_casillas_tiempo()
        self.forzar_refresco_reloj()

    def iniciar_tiempo(self):
        if self.estado.cronometro.iniciar():
            self.avisar("Cronómetro en marcha.", 'ok')
        elif self.estado.cronometro.restante == 0:
            self.avisar("Fija un tiempo antes de iniciar (botón SET).", 'error')

    def pausar_tiempo(self):
        if self.estado.cronometro.pausar():
            self.avisar("Cronómetro en pausa.", 'alerta')

    def alternar_tiempo(self, event=None):
        self.estado.cronometro.alternar()
        self.forzar_refresco_reloj()

    def sincronizar_casillas_tiempo(self):
        segundos = self.estado.cronometro.restante
        self.e_min.delete(0, "end"); self.e_min.insert(0, str(segundos // 60))
        self.e_sec.delete(0, "end"); self.e_sec.insert(0, f"{segundos % 60:02d}")

    def forzar_refresco_reloj(self):
        """Repinta el reloj ya mismo, sin esperar a que cambie el segundo."""
        self._ultimo_segundo_pintado = None
        if not self.tablero.actualizar_timer(self.estado):
            self.solicitar_redibujado()
        self.actualizar_reloj_panel()

    # ==========================================================================
    # MARCADOR
    # ==========================================================================
    def mod(self, idx, delta, tipo):
        """Suma o resta puntos ('p') o faltas ('f') a un equipo."""
        if tipo == 'p':
            cambiado = self.estado.sumar_puntos(idx, delta)
        else:
            cambiado = self.estado.sumar_faltas(idx, delta)
        if not cambiado:
            return
        self.refrescar_marcador_panel()
        self.solicitar_redibujado()

    def refrescar_marcador_panel(self):
        """Deja el panel del operador igual que el tablero del público."""
        for i, equipo in enumerate(self.estado.equipos):
            if i < len(self.lbls_puntos_ctrl):
                self.lbls_puntos_ctrl[i].config(text=str(equipo.puntos))
        self.refrescar_luces_faltas()
        self.actualizar_botones_historial()

    def refrescar_luces_faltas(self):
        """Enciende el semáforo de faltas del panel igual que el del tablero."""
        color_falta = self.estado.diseno.color_faltas
        for i, equipo in enumerate(self.estado.equipos):
            if i >= len(self.luces_faltas):
                continue
            for k, punto in enumerate(self.luces_faltas[i]):
                try:
                    punto.config(fg=color_falta if k < equipo.faltas else "#555")
                except tk.TclError:
                    pass

    def actualizar_botones_historial(self):
        estado_deshacer = "normal" if self.estado.puede_deshacer else "disabled"
        estado_rehacer = "normal" if self.estado.puede_rehacer else "disabled"
        for boton, valor in ((self.btn_deshacer, estado_deshacer),
                             (self.btn_rehacer, estado_rehacer)):
            try:
                boton.config(state=valor)
            except tk.TclError:
                pass

    def deshacer(self, event=None):
        if self.estado.deshacer():
            self.refrescar_marcador_panel()
            self.solicitar_redibujado()
            self.avisar("Jugada deshecha.")

    def rehacer(self, event=None):
        if self.estado.rehacer():
            self.refrescar_marcador_panel()
            self.solicitar_redibujado()
            self.avisar("Jugada rehecha.")

    def reiniciar_marcador(self, event=None):
        if not messagebox.askyesno("Reiniciar marcador",
                                   "¿Poner en cero los puntos y las faltas de todos los equipos?\n"
                                   "Los nombres y el diseño se conservan."):
            return
        self.estado.reiniciar_marcador()
        self.refrescar_marcador_panel()
        self.sincronizar_casillas_tiempo()
        self.forzar_refresco_reloj()
        self.solicitar_redibujado()
        self.avisar("Marcador reiniciado.", 'ok')

    def actualizar_nombre_live(self, idx):
        self.estado.renombrar(idx, self.entries_nombres[idx].get())
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def actualizar_estructura_equipos(self):
        self.estado.ajustar_numero_equipos(self.num_equipos_var.get())
        self.num_equipos_var.set(len(self.estado.equipos))
        self.dibujar_tiras_equipos()
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def elegir_color_equipo(self, idx):
        actual = self.estado.equipos[idx].color
        color = colorchooser.askcolor(color=actual, title="Color del equipo")[1]
        if not color:
            return
        self.estado.pintar_equipo(idx, color)
        self.botones_color[idx].config(bg=color)
        self.solicitar_redibujado()
        self.programar_autoguardado()

    # ==========================================================================
    # DISEÑO
    # ==========================================================================
    def upd_lay(self, attr, valor):
        """Aplica el valor de un slider al diseño respetando su tipo."""
        actual = getattr(self.estado.diseno, attr)
        if isinstance(actual, int) and not isinstance(actual, bool):
            setattr(self.estado.diseno, attr, int(float(valor)))
        else:
            setattr(self.estado.diseno, attr, float(valor))
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def cambiar_visibilidad(self, attr, var):
        setattr(self.estado.diseno, attr, bool(var.get()))
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def cambiar_pos_timer(self, event=None):
        self.estado.diseno.timer_position = self.combo_timer.get()
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def cambiar_segundos_alerta(self):
        try:
            self.estado.diseno.segundos_alerta = int(self.var_alerta.get())
        except ValueError:
            return
        self.forzar_refresco_reloj()
        self.programar_autoguardado()

    def elegir_color_diseno(self, attr):
        actual = getattr(self.estado.diseno, attr)
        color = colorchooser.askcolor(color=actual, title="Elige un color")[1]
        if not color:
            return
        setattr(self.estado.diseno, attr, color)
        self.botones_color_diseno[attr].config(bg=color)
        self.forzar_refresco_reloj()
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def set_font(self, nombre, destino):
        if destino == 'names':
            self.estado.diseno.font_family = nombre
        else:
            self.estado.diseno.font_score = nombre
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def restablecer_diseno(self):
        if not messagebox.askyesno("Restablecer diseño",
                                   "¿Volver al diseño por defecto?\n"
                                   "Se conservan los equipos, el marcador y los sonidos."):
            return
        fondo, logo = self.estado.diseno.fondo_path, self.estado.diseno.logo_path
        from match_state import Diseno
        self.estado.diseno = Diseno()
        self.estado.diseno.fondo_path, self.estado.diseno.logo_path = fondo, logo
        self.reconstruir_controles_diseno()
        self.solicitar_redibujado()
        self.programar_autoguardado()
        self.avisar("Diseño restablecido.", 'ok')

    def reconstruir_controles_diseno(self):
        """Vuelve a sincronizar los widgets tras cargar o restablecer un diseño."""
        d = self.estado.diseno
        self.ver_timer.set(d.ver_timer)
        self.ver_faltas.set(d.ver_faltas)
        self.var_outline.set(d.ver_outline)
        self.ver_barra_color.set(d.ver_barra_color)
        try:
            self.combo_timer.set(d.timer_position)
            self.var_alerta.set(str(d.segundos_alerta))
            self.combo_font_nombres.set(d.font_family)
            self.combo_font_score.set(d.font_score)
            for attr, boton in self.botones_color_diseno.items():
                boton.config(bg=getattr(d, attr))
            # Los sliders también deben reflejar el preset recién cargado, o el
            # siguiente arrastre devolvería el valor viejo de golpe.
            for attr, slider in self.sliders_diseno.items():
                slider.set(getattr(d, attr))
        except (tk.TclError, AttributeError):
            pass

    # --- Imágenes -----------------------------------------------------------
    def cambiar_fondo(self):
        ruta = filedialog.askopenfilename(
            title="Elige la imagen de fondo",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif"), ("Todos", "*.*")])
        if not ruta:
            return
        self.tablero.cache.olvidar(ruta)
        self.estado.diseno.fondo_path = ruta
        self.redibujar_ahora()
        if self.tablero.cache.fallo(ruta):
            self.estado.diseno.fondo_path = ""
            self.redibujar_ahora()
            messagebox.showerror("Imagen no válida",
                                 "No se pudo abrir esa imagen.\nPrueba con un archivo JPG o PNG.")
            return
        self.programar_autoguardado()
        self.avisar(f"Fondo: {os.path.basename(ruta)}")

    def quitar_fondo(self):
        self.estado.diseno.fondo_path = ""
        self.solicitar_redibujado()
        self.programar_autoguardado()

    def cambiar_logo(self):
        ruta = filedialog.askopenfilename(
            title="Elige el logo",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif"), ("Todos", "*.*")])
        if not ruta:
            return
        self.tablero.cache.olvidar(ruta)
        self.estado.diseno.logo_path = ruta
        self.redibujar_ahora()
        if self.tablero.cache.fallo(ruta):
            self.estado.diseno.logo_path = ""
            self.redibujar_ahora()
            messagebox.showerror("Imagen no válida", "No se pudo abrir ese logo.")
            return
        self.programar_autoguardado()
        self.avisar(f"Logo: {os.path.basename(ruta)}")

    def quitar_logo(self):
        self.estado.diseno.logo_path = ""
        self.solicitar_redibujado()
        self.programar_autoguardado()

    # ==========================================================================
    # PANTALLA COMPLETA
    # ==========================================================================
    def alternar_pantalla_completa(self, event=None):
        """
        Usa el modo pantalla completa nativo de Tk, que funciona igual en
        Windows, Linux y macOS y respeta el monitor donde esté la ventana.
        """
        self.poner_pantalla_completa(not self.is_fullscreen)

    def poner_pantalla_completa(self, activar):
        try:
            self.win_proj.attributes("-fullscreen", bool(activar))
            self.is_fullscreen = bool(activar)
        except tk.TclError:
            # Respaldo para gestores de ventanas antiguos: ventana sin bordes.
            self.win_proj.overrideredirect(bool(activar))
            try:
                self.win_proj.state('zoomed' if activar else 'normal')
            except tk.TclError:
                if activar:
                    self.win_proj.geometry(
                        f"{self.win_proj.winfo_screenwidth()}x{self.win_proj.winfo_screenheight()}+0+0")
            self.is_fullscreen = bool(activar)
        self.solicitar_redibujado()

    def salir_pantalla_completa(self, event=None):
        if self.is_fullscreen:
            self.poner_pantalla_completa(False)

    # ==========================================================================
    # SONIDOS
    # ==========================================================================
    def recargar_sonidos_guardados(self):
        """Reabre los efectos cuyas rutas venían en las preferencias."""
        for i, ranura in enumerate(self.estado.sonidos):
            if ranura.path:
                self.abrir_sonido(i, ranura.path, avisar_error=False)
        self.aplicar_volumen()

    def abrir_sonido(self, idx, ruta, avisar_error=True):
        ranura = self.estado.sonidos[idx]
        ranura.path = ruta
        ranura.obj = None
        if not AUDIO_ENABLED:
            self.marcar_estado_sonido(idx, "Sin audio", "#ff8888")
            return False
        if not os.path.isfile(ruta):
            self.marcar_estado_sonido(idx, "No encontrado", "#ff8888")
            if avisar_error:
                messagebox.showerror("Archivo no encontrado", f"Ya no existe:\n{ruta}")
            return False
        try:
            ranura.obj = pygame.mixer.Sound(ruta)
            ranura.obj.set_volume(self.estado.volumen)
            self.marcar_estado_sonido(idx, os.path.basename(ruta), "#afa")
            return True
        except Exception as e:
            self.marcar_estado_sonido(idx, "Formato no válido", "#ff8888")
            if avisar_error:
                messagebox.showerror("No se pudo cargar",
                                     f"{os.path.basename(ruta)}\n\nDetalle: {e}")
            return False

    def marcar_estado_sonido(self, idx, texto, color):
        try:
            self.lbls_estado_sonido[idx].config(text=texto, fg=color)
        except (AttributeError, IndexError, tk.TclError):
            pass

    def cargar_sonido(self, idx):
        ruta = filedialog.askopenfilename(
            title=f"Efecto para el botón #{idx + 1}",
            filetypes=[("Audio", "*.mp3 *.wav *.ogg"), ("Todos", "*.*")])
        if not ruta:
            return
        if self.abrir_sonido(idx, ruta):
            self.programar_autoguardado()
            self.avisar(f"FX {idx + 1}: {os.path.basename(ruta)}")

    def vaciar_sonido(self, idx):
        ranura = self.estado.sonidos[idx]
        ranura.path = ""
        ranura.obj = None
        self.marcar_estado_sonido(idx, "Vacío", "#666")
        self.programar_autoguardado()

    def update_sound_name(self, idx, nombre):
        self.estado.sonidos[idx].nombre = nombre[:24]
        self.botones_sonido_live[idx].config(text=nombre[:24])
        self.programar_autoguardado()

    def play_sound(self, idx):
        """Reproduce un efecto y hace un destello en el botón del panel."""
        ranura = self.estado.sonidos[idx]
        if not ranura.cargado:
            self.avisar(f"El botón #{idx + 1} no tiene ningún efecto cargado.", 'error')
            return
        ranura.obj.stop()
        ranura.obj.play()
        boton = self.botones_sonido_live[idx]
        # Color fijo, no el actual: si se pulsa dos veces seguidas el botón
        # ya no se queda encendido para siempre (fallo de la versión 1).
        boton.config(bg=ACENTO)
        self.root.after(180, lambda b=boton: b.winfo_exists() and b.config(bg=COLOR_BOTON_FX))

    def detener_sonidos(self):
        if AUDIO_ENABLED:
            pygame.mixer.stop()
        self.avisar("Efectos detenidos.")

    def cambiar_volumen(self, valor):
        self.estado.volumen = max(0.0, min(int(float(valor)) / 100.0, 1.0))
        self.aplicar_volumen()
        self.programar_autoguardado()

    def aplicar_volumen(self):
        for ranura in self.estado.sonidos:
            if ranura.obj is not None:
                try:
                    ranura.obj.set_volume(self.estado.volumen)
                except Exception:
                    pass

    # ==========================================================================
    # PREFERENCIAS Y PRESETS
    # ==========================================================================
    def programar_autoguardado(self):
        """Guarda en segundo plano poco después del último cambio."""
        if self._id_autoguardado is not None:
            try:
                self.root.after_cancel(self._id_autoguardado)
            except tk.TclError:
                pass
        self._id_autoguardado = self.root.after(AUTOGUARDADO_MS, self.guardar_preferencias)

    def guardar_preferencias(self, ruta=None, avisar_error=True):
        self._id_autoguardado = None
        destino = ruta or self.ruta_preferencias
        try:
            guardar_json(self.estado.a_dict(), destino)
            return True
        except OSError as e:
            if avisar_error:
                self.avisar(f"No se pudieron guardar las preferencias: {e}", 'error')
            return False

    def cargar_preferencias(self, ruta=None, silencioso=False):
        origen = ruta or self.ruta_preferencias
        if not os.path.isfile(origen):
            return False
        try:
            self.estado.aplicar_dict(cargar_json(origen))
            return True
        except (OSError, ValueError) as e:
            if not silencioso:
                messagebox.showerror("Preset no válido",
                                     f"No se pudo leer el archivo.\n\nDetalle: {e}")
            else:
                print(f"Advertencia: preferencias ilegibles ({e}). Se usan las de fábrica.")
            return False

    def guardar_preset_como(self, event=None):
        ruta = filedialog.asksaveasfilename(
            title="Guardar preset del espectáculo", defaultextension=".json",
            initialfile="preset_match.json", filetypes=[("Preset", "*.json")])
        if not ruta:
            return
        if self.guardar_preferencias(ruta):
            self.avisar(f"Preset guardado: {os.path.basename(ruta)}", 'ok')

    def cargar_preset_desde(self, event=None):
        ruta = filedialog.askopenfilename(title="Cargar preset",
                                          filetypes=[("Preset", "*.json"), ("Todos", "*.*")])
        if not ruta or not self.cargar_preferencias(ruta):
            return
        self.aplicar_estado_a_la_interfaz()
        self.avisar(f"Preset cargado: {os.path.basename(ruta)}", 'ok')

    def aplicar_estado_a_la_interfaz(self):
        """Refresca todos los widgets tras cargar un preset."""
        self.num_equipos_var.set(len(self.estado.equipos))
        self.dibujar_tiras_equipos()
        self.reconstruir_controles_diseno()
        self.sincronizar_casillas_tiempo()
        for i, ranura in enumerate(self.estado.sonidos):
            if i < len(self.entries_sonido):
                self.entries_sonido[i].delete(0, "end")
                self.entries_sonido[i].insert(0, ranura.nombre)
            self.botones_sonido_live[i].config(text=ranura.nombre)
            self.marcar_estado_sonido(i, "Vacío", "#666")
        self.recargar_sonidos_guardados()
        self.scale_volumen.set(int(self.estado.volumen * 100))
        self.tablero.cache.olvidar()
        self.forzar_refresco_reloj()
        self.redibujar_ahora()

    # ==========================================================================
    # ATAJOS DE TECLADO
    # ==========================================================================
    def registrar_atajos(self):
        """Los mismos atajos en el panel y en el tablero, para no perder el foco."""
        enlaces = [
            ("<space>", self.atajo_espacio),
            ("<Control-z>", self.deshacer),
            ("<Control-Z>", self.deshacer),
            ("<Control-y>", self.rehacer),
            ("<Control-Y>", self.rehacer),
            ("<Control-s>", self.atajo_guardar),
            ("<Control-S>", self.atajo_guardar),
            ("<Control-r>", self.reiniciar_marcador),
            ("<Control-R>", self.reiniciar_marcador),
            ("<F11>", self.alternar_pantalla_completa),
            ("<Escape>", self.salir_pantalla_completa),
        ]
        for i in range(MAX_EQUIPOS):
            enlaces.append((f"<Key-{i + 1}>", lambda e, x=i: self.atajo_punto(x, 1)))
            enlaces.append((f"<Shift-Key-{i + 1}>", lambda e, x=i: self.atajo_punto(x, -1)))
            enlaces.append((f"<F{i + 1}>", lambda e, x=i: self.atajo_falta(x)))

        for ventana in (self.root, self.win_proj):
            for secuencia, funcion in enlaces:
                try:
                    ventana.bind(secuencia, funcion)
                except tk.TclError:
                    pass

    def atajo_permitido(self):
        """Ignora los atajos mientras el operador escribe en una casilla."""
        foco = self.root.focus_get()
        return not isinstance(foco, (tk.Entry, ttk.Entry, tk.Spinbox, tk.Text))

    def atajo_espacio(self, event=None):
        if not self.atajo_permitido():
            return
        self.alternar_tiempo()
        return "break"

    def atajo_punto(self, idx, delta):
        if not self.atajo_permitido():
            return
        self.mod(idx, delta, 'p')
        return "break"

    def atajo_falta(self, idx):
        # F1..F6 no se confunden con la escritura: funcionan siempre.
        self.mod(idx, 1, 'f')
        return "break"

    def atajo_guardar(self, event=None):
        if self.guardar_preferencias():
            self.avisar("Preferencias guardadas.", 'ok')
        return "break"

    COLORES_AVISO = {'info': TEXTO_TENUE, 'ok': AVISO_OK,
                     'alerta': AVISO_ALERTA, 'error': AVISO_ERROR}

    def avisar(self, mensaje, tipo='info'):
        """Escribe en la barra de estado inferior del panel."""
        try:
            self.estado_var.set(mensaje)
            self.lbl_estado.config(fg=self.COLORES_AVISO.get(tipo, TEXTO_TENUE))
        except (AttributeError, tk.TclError):
            pass

    # ==========================================================================
    # CONTROL REMOTO
    # ==========================================================================
    def alternar_remoto(self):
        if self.remoto and self.remoto.activo:
            self.detener_remoto()
        else:
            self.iniciar_remoto()

    def iniciar_remoto(self):
        if not REMOTE_ENABLED:
            return
        try:
            puerto = int(self.remote_port_var.get())
            if not (1024 <= puerto <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Puerto inválido",
                                 "Escribe un número de puerto entre 1024 y 65535.")
            return

        # Reutilizamos el PIN ya mostrado para no obligar a re-emparejar el celular.
        pin_previo = self.remoto.pin if self.remoto else None
        self.remoto = ControlRemoto(self.estado_para_remoto, puerto=puerto, pin=pin_previo)
        try:
            self.remoto.iniciar()
        except OSError as e:
            self.remoto = None
            messagebox.showerror("No se pudo encender",
                                 f"El puerto {puerto} no está disponible.\n\n"
                                 f"Prueba con otro (ej. 8771).\n\nDetalle: {e}")
            return

        self.remote_pin_var.set(self.remoto.pin)
        self.remote_url_var.set(self.remoto.url)
        self.btn_remoto.config(text="⏹ APAGAR", bg=ROJO)
        self.entry_puerto.config(state="disabled")
        self.avisar(f"Mando a distancia activo en {self.remoto.url}", 'ok')

    def detener_remoto(self):
        if not self.remoto:
            return
        self.remoto.detener()
        self.remote_url_var.set("Servidor apagado")
        # Los widgets ya no existen si estamos cerrando la aplicación.
        try:
            self.btn_remoto.config(text="▶ ENCENDER", bg=VERDE)
            self.entry_puerto.config(state="normal")
            self.avisar("Mando a distancia apagado.", 'alerta')
        except tk.TclError:
            pass

    def regenerar_pin(self):
        """Cambia el PIN. Los celulares ya emparejados deberán escribir el nuevo."""
        if not REMOTE_ENABLED:
            return
        nuevo = generar_pin()
        if self.remoto:
            self.remoto.pin = nuevo
        self.remote_pin_var.set(nuevo)
        self.avisar("PIN nuevo generado: los celulares deben volver a emparejarse.", 'alerta')

    def estado_para_remoto(self):
        """Foto del estado para el celular. La lee el hilo del servidor: solo datos."""
        return self.estado.resumen()

    def bombear_comandos_remotos(self):
        """Ejecuta en el hilo de Tkinter los comandos que llegaron por la red."""
        if self.remoto and self.remoto.activo:
            comandos = self.remoto.vaciar_comandos()
            for comando in comandos:
                try:
                    self.aplicar_comando_remoto(comando)
                except Exception as e:
                    print(f"Comando remoto ignorado ({comando}): {e}")
        self._id_remoto = self.root.after(REMOTE_POLL_MS, self.bombear_comandos_remotos)

    def aplicar_comando_remoto(self, cmd):
        """Traduce un comando del celular a la acción equivalente del panel."""
        accion = cmd.get('accion')

        if accion in ('puntos', 'faltas'):
            idx = int(cmd.get('equipo', -1))
            delta = 1 if int(cmd.get('delta', 1)) >= 0 else -1
            if self.estado.indice_valido(idx):
                self.mod(idx, delta, 'p' if accion == 'puntos' else 'f')

        elif accion == 'timer_start':
            self.iniciar_tiempo()
            self.forzar_refresco_reloj()
        elif accion == 'timer_pause':
            self.pausar_tiempo()
            self.forzar_refresco_reloj()
        elif accion == 'timer_set':
            self.estado.cronometro.fijar(int(cmd.get('segundos', 0)))
            self.sincronizar_casillas_tiempo()
            self.forzar_refresco_reloj()
        elif accion == 'timer_ajustar':
            self.ajustar_tiempo(int(cmd.get('segundos', 0)))
        elif accion == 'deshacer':
            self.deshacer()
        elif accion == 'sonido':
            slot = int(cmd.get('slot', -1))
            if 0 <= slot < len(self.estado.sonidos):
                self.play_sound(slot)
        elif accion == 'detener_sonidos':
            self.detener_sonidos()

    # ==========================================================================
    # CIERRE
    # ==========================================================================
    def cerrar_app(self):
        """Guarda las preferencias, apaga el mando a distancia y cierra."""
        # Cancelamos los bucles pendientes: si no, Tk intenta ejecutarlos sobre
        # una ventana ya destruida y escupe errores en la consola al salir.
        for id_pendiente in (self._id_tic, self._id_remoto, self._id_refinado,
                             self._id_autoguardado):
            if id_pendiente is not None:
                try:
                    self.root.after_cancel(id_pendiente)
                except (tk.TclError, ValueError):
                    pass
        self._id_tic = self._id_remoto = self._id_refinado = self._id_autoguardado = None

        self.guardar_preferencias(avisar_error=False)
        self.detener_remoto()
        if AUDIO_ENABLED:
            try:
                pygame.mixer.stop()
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    ImproMatchApp()
