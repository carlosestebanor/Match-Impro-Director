"""
MATCH DE IMPRO - DIRECTOR (Versión Community)
------------------------------------------------------------------------------
Software de control para espectáculos de Match de Improvisación y competencias.
Gestiona cronómetro, puntajes, faltas, efectos de sonido y proyección multimedia.

Autor: Corporación Acción Impro
Ubicación: Medellín, Colombia
Año: 2026
Licencia: Creative Commons Atribución 4.0 Internacional (CC BY 4.0)
Usted es libre de compartir y adaptar este código siempre que reconozca la autoría.
------------------------------------------------------------------------------
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser, font
from PIL import Image, ImageTk # Librería Pillow para manejo avanzado de imágenes
import pygame # Librería para efectos de sonido
import sys
import os

# --- CONFIGURACIÓN DE AUDIO ---
# Intentamos iniciar el mixer. Si falla (ej. no hay tarjeta de sonido), el programa sigue funcionando sin audio.
AUDIO_ENABLED = False
try:
    pygame.mixer.init()
    AUDIO_ENABLED = True
except:
    print("Advertencia: No se detectó dispositivo de audio. El modo sonido estará desactivado.")

# --- CONTROL REMOTO (opcional) ---
# Módulo propio, solo librería estándar. Si falta el archivo, la app sigue funcionando.
try:
    from remote_control import ControlRemoto
    REMOTE_ENABLED = True
except Exception:
    ControlRemoto = None
    REMOTE_ENABLED = False
    print("Advertencia: No se encontró 'remote_control.py'. El mando a distancia estará desactivado.")

# Cada cuánto (ms) el panel revisa los comandos que llegaron desde el celular.
REMOTE_POLL_MS = 120

class ImproMatchApp:
    def __init__(self):
        # Configuración de la Ventana Principal (Panel de Control)
        self.root = tk.Tk()
        self.root.title("Match Impro Director - Acción Impro 2026")
        self.root.geometry("540x950")
        self.root.configure(bg="#222") # Tema Oscuro
        
        # --- VARIABLES DE ESTADO (MODELO DE DATOS) ---
        self.equipos = [] # Lista de diccionarios con datos de cada equipo
        self.num_equipos_var = tk.IntVar(value=3) # Por defecto 3 equipos
        self.fondo_path = None
        self.logo_path = None
        
        self.tiempo_restante = 240 # 4 minutos en segundos
        self.corriendo = False # Estado del reloj
        
        # Slots para 6 efectos de sonido
        self.sonidos = [{'name': f'FX {i+1}', 'path': None, 'obj': None} for i in range(6)]
        
        # --- VARIABLES DE DISEÑO (VIEW MODEL) ---
        # Controlan posiciones, tamaños y colores de la proyección
        self.scale_factor = 1.0       # Zoom general
        self.name_scale = 1.0         # Tamaño nombres
        self.offset_global_y = 0.0    # Mover todo verticalmente
        self.offset_names = 0.0
        self.offset_scores = 0.0
        self.offset_timer = 0.0
        self.offset_x = 0.0
        
        # Configuración del Logo
        self.logo_scale = 0.5
        self.logo_offset_y = -0.4     # Posición por defecto (Arriba)
        
        # Estilos por defecto
        self.font_family = "Arial"
        self.font_score = "Impact"    # Fuente gruesa para números
        self.color_nombres = "#ffffff"
        self.color_puntos = "#ffcc00" # Amarillo clásico
        self.color_faltas = "#ff0000" # Rojo
        self.color_caja = "#000000"   # Fondo negro de marcadores
        
        self.box_padding = 1.0        # Margen interno de las cajas negras
        self.corner_radius = 20       # Redondez de las esquinas
        self.timer_position = "Abajo" # Ubicación del reloj
        
        # Interruptores de Visibilidad
        self.ver_timer = tk.BooleanVar(value=True)
        self.ver_faltas = tk.BooleanVar(value=True)
        self.var_outline = tk.BooleanVar(value=True) # Borde negro en texto
        
        self.is_fullscreen = False # Estado de pantalla completa

        # --- CONTROL REMOTO ---
        self.remoto = None                    # Instancia de ControlRemoto cuando está encendido
        self.remote_port_var = tk.StringVar(value="8770")
        self.remote_pin_var = tk.StringVar(value="------")
        self.remote_url_var = tk.StringVar(value="Servidor apagado")

        # --- INICIALIZACIÓN DE VENTANAS ---
        # Ventana Secundaria (Proyector)
        self.win_proj = tk.Toplevel(self.root)
        self.win_proj.title("Tablero Público (Proyector)")
        self.win_proj.geometry("800x450")
        self.win_proj.configure(bg="black")
        
        # BINDINGS (Eventos de Teclado/Mouse)
        # F11 activa pantalla completa en el monitor donde esté la ventana
        self.win_proj.bind("<F11>", self.toggle_full_event)
        
        # Lienzo de dibujo (Canvas)
        self.canvas = tk.Canvas(self.win_proj, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        # Doble clic solo en el lienzo para evitar conflictos
        self.canvas.bind("<Double-Button-1>", self.toggle_full_event) 
        
        # Redibujar si se cambia el tamaño de la ventana
        self.win_proj.bind("<Configure>", self.redibujar_pantalla)

        # Cargar datos iniciales y construir interfaz
        self.reconstruir_equipos_data()
        self.construir_panel_control()
        self.redibujar_pantalla()

        # Cierre ordenado (apaga el servidor remoto antes de salir)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_app)
        # Atención permanente a los comandos que llegan del celular
        self.root.after(REMOTE_POLL_MS, self.bombear_comandos_remotos)

        self.root.mainloop() # Bucle principal de la aplicación

    def cerrar_app(self):
        """Apaga el mando a distancia y cierra la aplicación."""
        self.detener_remoto()
        self.root.destroy()

    # --- LÓGICA DE DATOS ---
    def reconstruir_equipos_data(self):
        """Ajusta la lista de equipos según el número seleccionado (2 a 4)."""
        n = self.num_equipos_var.get()
        actual = len(self.equipos)
        if n > actual:
            colores_default = ["ROJO", "AMARILLO", "AZUL", "VERDE"]
            for i in range(actual, n):
                nom = colores_default[i] if i < 4 else f"EQ {i+1}"
                self.equipos.append({'nombre': nom, 'puntos': 0, 'faltas': 0})
        elif n < actual:
            self.equipos = self.equipos[:n]

    # --- INTERFAZ GRÁFICA (PANEL DE CONTROL) ---
    def construir_panel_control(self):
        """Construye las pestañas y controles del operador."""
        # Limpieza por si reconstruimos la interfaz
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Notebook): widget.destroy()

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=5, pady=5)

        # === PESTAÑA 1: EN VIVO (Controles rápidos) ===
        tab_game = tk.Frame(nb, bg="#222")
        nb.add(tab_game, text="🔴 EN VIVO")
        
        # Sección Cronómetro
        fr_t = tk.LabelFrame(tab_game, text="CRONÓMETRO", font=("Arial", 10, "bold"), bg="#222", fg="white")
        fr_t.pack(fill="x", padx=10, pady=5)
        f_in = tk.Frame(fr_t, bg="#222"); f_in.pack()
        
        # Entradas de Minutos y Segundos
        self.e_min = tk.Entry(f_in, width=3, font=("Arial", 14), justify="center"); self.e_min.insert(0,"4"); self.e_min.pack(side="left")
        tk.Label(f_in, text=":", bg="#222", fg="white").pack(side="left")
        self.e_sec = tk.Entry(f_in, width=3, font=("Arial", 14), justify="center"); self.e_sec.insert(0,"00"); self.e_sec.pack(side="left")
        
        f_btn = tk.Frame(fr_t, bg="#222"); f_btn.pack(pady=5)
        tk.Button(f_btn, text="SET", command=self.set_tiempo).pack(side="left")
        tk.Button(f_btn, text="▶ INICIO", bg="#afa", command=self.iniciar_tiempo).pack(side="left", padx=5)
        tk.Button(f_btn, text="⏸ PAUSA", bg="#fea", command=self.pausar_tiempo).pack(side="left")

        # Configuración rápida de Equipos
        fr_cfg = tk.Frame(tab_game, bg="#222"); fr_cfg.pack(fill="x", padx=10)
        tk.Label(fr_cfg, text="Equipos:", fg="#aaa", bg="#222").pack(side="left")
        tk.Spinbox(fr_cfg, from_=2, to=4, textvariable=self.num_equipos_var, width=3, command=self.actualizar_estructura_equipos).pack(side="left", padx=5)
        
        # Contenedor dinámico de equipos
        self.frame_container_eq = tk.Frame(tab_game, bg="#222")
        self.frame_container_eq.pack(fill="both", expand=True, padx=5, pady=5)
        self.dibujar_tiras_equipos()

        # Botonera de Sonidos (Soundbar)
        fr_snd_live = tk.LabelFrame(tab_game, text="EFECTOS", bg="#222", fg="#00d4ff", font=("Arial", 10, "bold"))
        fr_snd_live.pack(fill="x", padx=10, pady=10, side="bottom")
        self.botones_sonido_live = []
        for i in range(6):
            # Botones grandes para lanzar audio
            btn = tk.Button(fr_snd_live, text=self.sonidos[i]['name'], bg="#333", fg="white", font=("Arial", 9, "bold"), height=2, command=lambda x=i: self.play_sound(x))
            r = 0 if i < 3 else 1; c = i % 3
            btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
            fr_snd_live.grid_columnconfigure(c, weight=1)
            self.botones_sonido_live.append(btn)

        # === PESTAÑA 2: DISEÑO (Personalización) ===
        tab_design = tk.Frame(nb, bg="#222")
        nb.add(tab_design, text="🎨 DISEÑO")
        
        # Carga de Imágenes
        fr_img = tk.LabelFrame(tab_design, text="Imágenes (Fondo y Logo)", bg="#222", fg="white")
        fr_img.pack(fill="x", padx=10, pady=5)
        tk.Button(fr_img, text="🖼 Cambiar Fondo", command=self.cambiar_fondo, bg="#444", fg="white").pack(fill="x", padx=5, pady=2)
        
        f_logo = tk.Frame(fr_img, bg="#222"); f_logo.pack(fill="x", pady=5)
        tk.Button(f_logo, text="⭐ Cargar Logo", command=self.cambiar_logo, bg="#444", fg="white").pack(side="left", padx=5, expand=True)
        tk.Button(f_logo, text="❌ Quitar", command=self.quitar_logo, bg="#522", fg="white").pack(side="left", padx=5)
        
        # Sliders para el Logo
        f_sl_logo = tk.Frame(fr_img, bg="#222"); f_sl_logo.pack(fill="x")
        tk.Label(f_sl_logo, text="Tam. Logo", bg="#222", fg="#aaa", font=("Arial", 8)).pack(side="left")
        tk.Scale(f_sl_logo, from_=0.1, to=2.0, resolution=0.1, orient="horizontal", bg="#222", fg="white", bd=0, highlightthickness=0, command=lambda v: self.upd_lay('logo_scale', v)).pack(side="left", fill="x", expand=True)
        
        f_sl_logoy = tk.Frame(fr_img, bg="#222"); f_sl_logoy.pack(fill="x")
        tk.Label(f_sl_logoy, text="Pos. Y Logo", bg="#222", fg="#aaa", font=("Arial", 8)).pack(side="left")
        tk.Scale(f_sl_logoy, from_=-0.5, to=0.5, resolution=0.01, orient="horizontal", bg="#222", fg="white", bd=0, highlightthickness=0, command=lambda v: self.upd_lay('logo_offset_y', v)).pack(side="left", fill="x", expand=True)
        self.upd_lay('logo_offset_y', self.logo_offset_y)

        # Visibilidad
        fr_vis = tk.LabelFrame(tab_design, text="Visibilidad", bg="#222", fg="#00ff88")
        fr_vis.pack(fill="x", padx=10, pady=5)
        tk.Checkbutton(fr_vis, text="Timer", variable=self.ver_timer, bg="#222", fg="white", selectcolor="#444", command=self.redibujar_pantalla).pack(side="left", padx=10)
        tk.Checkbutton(fr_vis, text="Faltas", variable=self.ver_faltas, bg="#222", fg="white", selectcolor="#444", command=self.redibujar_pantalla).pack(side="left", padx=10)

        # Colores
        fr_col = tk.LabelFrame(tab_design, text="Colores", bg="#222", fg="white")
        fr_col.pack(fill="x", padx=10, pady=5)
        def pick(t): # Helper para elegir color
            c = colorchooser.askcolor()[1]
            if c: setattr(self, f"color_{t}", c); self.redibujar_pantalla()
        tk.Button(fr_col, text="Nombres", bg=self.color_nombres, command=lambda: pick('nombres')).pack(side="left", expand=True, fill="x", padx=1)
        tk.Button(fr_col, text="Puntos", bg=self.color_puntos, command=lambda: pick('puntos')).pack(side="left", expand=True, fill="x", padx=1)
        tk.Button(fr_col, text="Faltas", bg=self.color_faltas, command=lambda: pick('faltas')).pack(side="left", expand=True, fill="x", padx=1)
        tk.Button(fr_col, text="Cajas", bg="grey", command=lambda: pick('caja')).pack(side="left", expand=True, fill="x", padx=1)

        # Geometría y Posiciones
        fr_lay = tk.LabelFrame(tab_design, text="Geometría", bg="#222", fg="white")
        fr_lay.pack(fill="x", padx=10, pady=5)
        
        # Posición del Timer
        f_tim_pos = tk.Frame(fr_lay, bg="#222"); f_tim_pos.pack(fill="x", padx=5, pady=5)
        tk.Label(f_tim_pos, text="Base Timer:", bg="#222", fg="#aaa").pack(side="left")
        self.combo_timer = ttk.Combobox(f_tim_pos, values=["Arriba", "Abajo"], state="readonly", width=8)
        self.combo_timer.set(self.timer_position)
        self.combo_timer.pack(side="left", padx=5)
        self.combo_timer.bind("<<ComboboxSelected>>", self.cambiar_pos_timer)
        
        tk.Button(f_tim_pos, text="⛶ PANTALLA COMPLETA (F11)", bg="#00d4ff", fg="black", font=("Arial", 8, "bold"), command=lambda: self.toggle_full_event(None)).pack(side="right")

        # Sliders Genéricos
        def mk_sl(txt, vmin, vmax, res, attr):
            f = tk.Frame(fr_lay, bg="#222"); f.pack(fill="x", pady=1)
            tk.Label(f, text=txt, bg="#222", fg="#ddd", width=20, anchor="w", font=("Arial", 8)).pack(side="left")
            s = tk.Scale(f, from_=vmin, to=vmax, resolution=res, orient="horizontal", bg="#222", fg="white", highlightthickness=0, bd=0, command=lambda v: self.upd_lay(attr, v))
            s.set(getattr(self, attr)); s.pack(side="right", fill="x", expand=True)

        mk_sl("Pos. Vertical (Todo)", -0.5, 0.5, 0.01, 'offset_global_y')
        mk_sl("Offset Nombres", -0.2, 0.2, 0.01, 'offset_names')
        mk_sl("Offset Puntos", -0.2, 0.2, 0.01, 'offset_scores')
        mk_sl("Ajuste Timer", -0.5, 0.5, 0.01, 'offset_timer')
        tk.Label(fr_lay, text="--- GENERAL ---", bg="#222", fg="#666", font=("Arial", 7)).pack(pady=2)
        mk_sl("Tam. Nombres", 0.5, 3.0, 0.1, 'name_scale')
        mk_sl("Zoom General", 0.5, 2.0, 0.1, 'scale_factor')
        mk_sl("Margen Cajas", 0.5, 2.0, 0.1, 'box_padding')
        tk.Checkbutton(fr_lay, text="Outline Nombres (Borde Negro)", variable=self.var_outline, bg="#222", fg="white", selectcolor="#444", command=self.redibujar_pantalla).pack(pady=5)

        # Selección de Fuentes
        fr_f = tk.LabelFrame(tab_design, text="Fuentes", bg="#222", fg="white")
        fr_f.pack(fill="x", padx=10)
        lst_f = [f for f in font.families() if not f.startswith("@")]; lst_f.sort()
        
        cb_fn = ttk.Combobox(fr_f, values=lst_f, state="readonly"); cb_fn.set("Arial"); cb_fn.pack(fill="x", pady=2)
        cb_fn.bind("<<ComboboxSelected>>", lambda e: self.set_font(cb_fn.get(), 'names'))
        
        cb_fs = ttk.Combobox(fr_f, values=lst_f, state="readonly"); cb_fs.set("Impact"); cb_fs.pack(fill="x", pady=2)
        cb_fs.bind("<<ComboboxSelected>>", lambda e: self.set_font(cb_fs.get(), 'score'))

        # === PESTAÑA 3: CONFIGURACIÓN DE SONIDOS ===
        tab_fx = tk.Frame(nb, bg="#222")
        nb.add(tab_fx, text="⚙ SONIDOS")
        tk.Label(tab_fx, text="CONFIGURAR BOTONES (6 SLOTS)", bg="#222", fg="#00d4ff", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Generar filas de configuración
        for i in range(6):
            fr_row = tk.Frame(tab_fx, bg="#333", pady=5); fr_row.pack(fill="x", padx=10, pady=2)
            tk.Label(fr_row, text=f"#{i+1}", bg="#333", fg="#888", width=3).pack(side="left")
            
            # Editar Nombre
            en_name = tk.Entry(fr_row, width=15); en_name.insert(0, self.sonidos[i]['name']); en_name.pack(side="left", padx=5)
            en_name.bind("<KeyRelease>", lambda event, idx=i, widget=en_name: self.update_sound_name(idx, widget.get()))
            
            # Cargar Archivo
            tk.Button(fr_row, text="📂", command=lambda x=i: self.cargar_sonido(x)).pack(side="left", padx=2)
            
            # Estado
            lbl_status = tk.Label(fr_row, text="Vacío", bg="#333", fg="#666", width=15, anchor="w", font=("Arial", 8)); lbl_status.pack(side="left", padx=5)
            self.sonidos[i]['lbl_widget'] = lbl_status
            
            # Test Play
            tk.Button(fr_row, text="▶", command=lambda x=i: self.play_sound(x), bg="#444", fg="white").pack(side="right", padx=5)

        # === PESTAÑA 4: CONTROL REMOTO ===
        tab_remote = tk.Frame(nb, bg="#222")
        nb.add(tab_remote, text="📡 REMOTO")
        self.construir_pestana_remoto(tab_remote)

    def construir_pestana_remoto(self, parent):
        """Pestaña para publicar el mando a distancia en la red local."""
        tk.Label(parent, text="MANDO A DISTANCIA (WiFi)", bg="#222", fg="#00d4ff",
                 font=("Arial", 12, "bold")).pack(pady=(10, 2))
        tk.Label(parent, text="Controla puntos, faltas, cronómetro y efectos\ndesde tu celular o tablet.",
                 bg="#222", fg="#aaa", font=("Arial", 9), justify="center").pack(pady=(0, 10))

        if not REMOTE_ENABLED:
            tk.Label(parent, text="⚠ Falta el archivo 'remote_control.py'.\nDescárgalo junto al programa para usar esta función.",
                     bg="#222", fg="#ff8888", font=("Arial", 9), justify="center").pack(pady=20)
            return

        # Puerto + interruptor
        fr_cfg = tk.LabelFrame(parent, text="Servidor", bg="#222", fg="white")
        fr_cfg.pack(fill="x", padx=10, pady=5)

        f_port = tk.Frame(fr_cfg, bg="#222"); f_port.pack(fill="x", padx=5, pady=5)
        tk.Label(f_port, text="Puerto:", bg="#222", fg="#aaa").pack(side="left")
        self.entry_puerto = tk.Entry(f_port, textvariable=self.remote_port_var, width=6, justify="center")
        self.entry_puerto.pack(side="left", padx=5)

        self.btn_remoto = tk.Button(f_port, text="▶ ENCENDER", bg="#1d7a4a", fg="white",
                                    font=("Arial", 9, "bold"), command=self.alternar_remoto)
        self.btn_remoto.pack(side="right", padx=5)

        # Datos de conexión
        fr_conn = tk.LabelFrame(parent, text="Datos de conexión", bg="#222", fg="#00ff88")
        fr_conn.pack(fill="x", padx=10, pady=5)

        tk.Label(fr_conn, text="Dirección (escríbela en el navegador del celular):",
                 bg="#222", fg="#aaa", font=("Arial", 8)).pack(anchor="w", padx=5, pady=(5, 0))
        self.lbl_url = tk.Entry(fr_conn, textvariable=self.remote_url_var, state="readonly",
                                readonlybackground="#111", fg="#00d4ff", justify="center",
                                font=("Consolas", 12, "bold"), bd=0)
        self.lbl_url.pack(fill="x", padx=5, pady=3)

        f_pin = tk.Frame(fr_conn, bg="#222"); f_pin.pack(fill="x", padx=5, pady=5)
        tk.Label(f_pin, text="PIN:", bg="#222", fg="#aaa").pack(side="left")
        tk.Label(f_pin, textvariable=self.remote_pin_var, bg="#222", fg="#ffcc00",
                 font=("Consolas", 18, "bold")).pack(side="left", padx=8)
        tk.Button(f_pin, text="🔄 Nuevo PIN", bg="#444", fg="white", font=("Arial", 8),
                  command=self.regenerar_pin).pack(side="right")

        tk.Label(parent, justify="left", bg="#222", fg="#888", font=("Arial", 8), anchor="w",
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

    # --- LÓGICA DE NEGOCIO ---
    def update_sound_name(self, idx, new_name):
        self.sonidos[idx]['name'] = new_name
        self.botones_sonido_live[idx].config(text=new_name)
        
    def cargar_sonido(self, idx):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.ogg")])
        if path:
            self.sonidos[idx]['path'] = path
            try:
                if AUDIO_ENABLED:
                    self.sonidos[idx]['obj'] = pygame.mixer.Sound(path)
                    self.sonidos[idx]['lbl_widget'].config(text=os.path.basename(path), fg="#afa")
            except: pass
            
    def play_sound(self, idx):
        """Reproduce un sonido y anima el botón en el panel."""
        snd = self.sonidos[idx]['obj']
        if snd:
            snd.stop(); snd.play()
            orig = self.botones_sonido_live[idx].cget("bg")
            self.botones_sonido_live[idx].config(bg="#00d4ff")
            self.root.after(200, lambda: self.botones_sonido_live[idx].config(bg=orig))
            
    def cambiar_pos_timer(self, event):
        self.timer_position = self.combo_timer.get(); self.redibujar_pantalla()
        
    def dibujar_tiras_equipos(self):
        """Dibuja los controles de cada equipo en la pestaña EN VIVO."""
        for widget in self.frame_container_eq.winfo_children(): widget.destroy()
        self.lbls_puntos_ctrl = []; self.entries_nombres = []
        
        for i, eq in enumerate(self.equipos):
            fr = tk.Frame(self.frame_container_eq, bg="#333", pady=5); fr.pack(fill="x", pady=2)
            
            # Nombre Editable
            en = tk.Entry(fr, bg="#222", fg="white", font=("Arial", 11, "bold"), justify="center")
            en.insert(0, eq['nombre']); en.pack(side="top", fill="x", padx=5)
            en.bind("<KeyRelease>", lambda event, idx=i: self.actualizar_nombre_live(idx, event))
            self.entries_nombres.append(en)
            
            f_ctrl = tk.Frame(fr, bg="#333"); f_ctrl.pack(fill="x", padx=5)
            
            # Control Puntos
            tk.Button(f_ctrl, text="-", width=3, bg="#444", fg="white", command=lambda x=i: self.mod(x, -1, 'p')).pack(side="left")
            l = tk.Label(f_ctrl, text=str(eq['puntos']), font=("Impact", 16), width=3, bg="#333", fg="#00d4ff")
            l.pack(side="left", padx=5); self.lbls_puntos_ctrl.append(l)
            tk.Button(f_ctrl, text="+", width=3, bg="#444", fg="white", command=lambda x=i: self.mod(x, 1, 'p')).pack(side="left")
            
            # Control Faltas
            tk.Button(f_ctrl, text="FALTA", bg="#d44", fg="white", font=("Arial", 8, "bold"), command=lambda x=i: self.mod(x, 1, 'f')).pack(side="right")
            tk.Button(f_ctrl, text="quitar", bg="#444", fg="#aaa", font=("Arial", 7), command=lambda x=i: self.mod(x, -1, 'f')).pack(side="right", padx=2)

    def actualizar_nombre_live(self, idx, event): self.equipos[idx]['nombre'] = self.entries_nombres[idx].get(); self.redibujar_pantalla()
    def actualizar_estructura_equipos(self): self.reconstruir_equipos_data(); self.dibujar_tiras_equipos(); self.redibujar_pantalla()
    
    # Manejo de Archivos (Fondo/Logo)
    def cambiar_fondo(self):
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.png *.jpeg")])
        if path: self.fondo_path = path; 
        if hasattr(self, 'pil_img_orig'): del self.pil_img_orig
        self.redibujar_pantalla()
    def cambiar_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg")])
        if path:
            self.logo_path = path
            if hasattr(self, 'pil_logo_orig'): del self.pil_logo_orig
            self.redibujar_pantalla()
    def quitar_logo(self): self.logo_path = None; self.redibujar_pantalla()
    
    # --- PANTALLA COMPLETA INTELIGENTE ---
    def toggle_full_event(self, event=None):
        """Activa/Desactiva el modo sin bordes maximizado en el monitor actual."""
        if self.is_fullscreen:
            self.win_proj.overrideredirect(False)
            self.win_proj.state('normal')
            self.is_fullscreen = False
        else:
            self.win_proj.overrideredirect(True)
            self.win_proj.state('zoomed') 
            self.is_fullscreen = True

    # --- MOTOR DE RENDERIZADO (CANVAS) ---
    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        """Dibuja un polígono con esquinas redondeadas."""
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def draw_text_multiline(self, x, y, text, font, fill, max_width):
        """Dibuja texto con ajuste automático de línea y outline opcional."""
        if self.var_outline.get():
             for ox in [-2, 0, 2]:
                for oy in [-2, 0, 2]:
                    if ox!=0 or oy!=0: self.canvas.create_text(x+ox, y+oy, text=text, font=font, fill="black", width=max_width, justify="center")
        self.canvas.create_text(x, y, text=text, font=font, fill=fill, width=max_width, justify="center")

    def redibujar_pantalla(self, event=None):
        """Dibuja todos los elementos en el Canvas del proyector."""
        self.canvas.delete("all")
        w = self.win_proj.winfo_width(); h = self.win_proj.winfo_height()
        
        # 1. Fondo
        if self.fondo_path:
            if not hasattr(self, 'pil_img_orig'): self.pil_img_orig = Image.open(self.fondo_path)
            img_r = self.pil_img_orig.resize((w, h), Image.Resampling.LANCZOS)
            self.tk_bg = ImageTk.PhotoImage(img_r)
            self.canvas.create_image(0, 0, image=self.tk_bg, anchor="nw")

        # 2. Logo
        if self.logo_path:
            if not hasattr(self, 'pil_logo_orig'): self.pil_logo_orig = Image.open(self.logo_path)
            base_logo_size = h * 0.2 * self.logo_scale
            aspect = self.pil_logo_orig.width / self.pil_logo_orig.height
            new_w = int(base_logo_size * aspect); new_h = int(base_logo_size)
            img_l = self.pil_logo_orig.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.tk_logo = ImageTk.PhotoImage(img_l)
            lx = w * 0.5; ly = (h * 0.5) + (h * self.logo_offset_y)
            self.canvas.create_image(lx, ly, image=self.tk_logo, anchor="center")

        # Configuración Base
        base_font = int(h * 0.05 * self.scale_factor)
        cx = w * 0.5 + (w * self.offset_x)
        
        cy_equipos = (h * 0.5) + (h * self.offset_global_y)
        if self.timer_position == "Arriba": cy_timer = (h * 0.15)
        else: cy_timer = (h * 0.85)
        cy_timer += (h * self.offset_timer)

        # 3. Timer (Condicional)
        if self.ver_timer.get():
            t_w = w * 0.25 * self.scale_factor * self.box_padding; t_h = h * 0.15 * self.scale_factor * self.box_padding
            min_sec = f"{self.tiempo_restante//60:02d}:{self.tiempo_restante%60:02d}"
            self.create_rounded_rect(cx-t_w/2, cy_timer-t_h/2, cx+t_w/2, cy_timer+t_h/2, radius=self.corner_radius, fill=self.color_caja)
            self.canvas.create_text(cx, cy_timer, text=min_sec, fill="white", font=(self.font_score, int(base_font*2.5)))

        # 4. Equipos
        cols = len(self.equipos); col_w = w / cols
        for i, eq in enumerate(self.equipos):
            x = (i * col_w) + (col_w / 2) + (w * self.offset_x)
            y_nm = cy_equipos - (h * 0.12) + (h * self.offset_names)
            y_pts_base = cy_equipos + (h * 0.02) + (h * self.offset_scores)
            
            # Nombre
            self.draw_text_multiline(x, y_nm, eq['nombre'], (self.font_family, int(base_font * self.name_scale), "bold"), self.color_nombres, max_width=col_w*0.9)
            
            # Puntos
            p_w = h * 0.2 * self.scale_factor * self.box_padding; p_h = p_w * 0.8
            self.create_rounded_rect(x-p_w/2, y_pts_base-p_h/2, x+p_w/2, y_pts_base+p_h/2, radius=self.corner_radius, fill=self.color_caja)
            self.canvas.create_text(x, y_pts_base, text=str(eq['puntos']), fill=self.color_puntos, font=(self.font_score, int(base_font*3)))
            
            # Faltas (Condicional)
            if self.ver_faltas.get():
                y_flt = y_pts_base + (h * 0.16)
                f_box_w = p_w * 1.0; f_box_h = p_h * 0.4
                self.create_rounded_rect(x-f_box_w/2, y_flt-f_box_h/2, x+f_box_w/2, y_flt+f_box_h/2, radius=self.corner_radius, fill=self.color_caja)
                radius_c = f_box_h * 0.3; gap = radius_c * 0.5; start_x = x - ((radius_c*2 * 3 + gap * 2) / 2) + radius_c
                for k in range(3):
                    dot_x = start_x + (k * (radius_c*2 + gap)); color = self.color_faltas if k < eq['faltas'] else "#333"
                    self.canvas.create_oval(dot_x-radius_c, y_flt-radius_c, dot_x+radius_c, y_flt+radius_c, fill=color, outline="")

    # --- CONTROL DE TIEMPO Y VALORES ---
    def set_font(self, font_name, target):
        if target == 'names': self.font_family = font_name
        else: self.font_score = font_name
        self.redibujar_pantalla()
    def upd_lay(self, param, val): setattr(self, param, float(val)); self.redibujar_pantalla()
    def mod(self, idx, d, type):
        eq = self.equipos[idx]
        if type == 'p':
            if eq['puntos'] + d >= 0: eq['puntos'] += d; self.lbls_puntos_ctrl[idx].config(text=str(eq['puntos']))
        else:
            if 0 <= eq['faltas'] + d <= 3: eq['faltas'] += d
        self.redibujar_pantalla()
    def set_tiempo(self):
        try: self.tiempo_restante = int(self.e_min.get())*60 + int(self.e_sec.get()); self.redibujar_pantalla()
        except: pass
    def iniciar_tiempo(self):
        if not self.corriendo: self.corriendo = True; self.loop()
    def pausar_tiempo(self): self.corriendo = False
    def loop(self):
        if self.corriendo and self.tiempo_restante > 0:
            self.tiempo_restante -= 1; self.redibujar_pantalla(); self.root.after(1000, self.loop)
        elif self.tiempo_restante == 0: self.corriendo = False

    # --- CONTROL REMOTO (SERVIDOR + PUENTE CON TKINTER) ---
    def alternar_remoto(self):
        """Enciende o apaga el mando a distancia según su estado actual."""
        if self.remoto and self.remoto.activo: self.detener_remoto()
        else: self.iniciar_remoto()

    def iniciar_remoto(self):
        if not REMOTE_ENABLED: return
        try:
            puerto = int(self.remote_port_var.get())
            if not (1024 <= puerto <= 65535): raise ValueError
        except ValueError:
            messagebox.showerror("Puerto inválido", "Escribe un número de puerto entre 1024 y 65535.")
            return

        # Reutilizamos el PIN ya mostrado para no obligar a re-emparejar el celular.
        pin_previo = self.remoto.pin if self.remoto else None
        self.remoto = ControlRemoto(self.estado_para_remoto, puerto=puerto, pin=pin_previo)
        try:
            self.remoto.iniciar()
        except OSError as e:
            self.remoto = None
            messagebox.showerror("No se pudo encender",
                                 f"El puerto {puerto} no está disponible.\n\nPrueba con otro (ej. 8771).\n\nDetalle: {e}")
            return

        self.remote_pin_var.set(self.remoto.pin)
        self.remote_url_var.set(self.remoto.url)
        self.btn_remoto.config(text="⏹ APAGAR", bg="#a32d2d")
        self.entry_puerto.config(state="disabled")

    def detener_remoto(self):
        if not self.remoto: return
        self.remoto.detener()
        self.remote_url_var.set("Servidor apagado")
        # Los widgets ya no existen si estamos cerrando la aplicación.
        try:
            self.btn_remoto.config(text="▶ ENCENDER", bg="#1d7a4a")
            self.entry_puerto.config(state="normal")
        except tk.TclError:
            pass

    def regenerar_pin(self):
        """Cambia el PIN. Los celulares ya emparejados deberán escribir el nuevo."""
        if not REMOTE_ENABLED: return
        from remote_control import generar_pin
        nuevo = generar_pin()
        if self.remoto: self.remoto.pin = nuevo
        self.remote_pin_var.set(nuevo)

    def estado_para_remoto(self):
        """Foto del estado actual para el celular. Se lee desde el hilo del servidor:
        solo datos simples, nunca widgets."""
        return {
            'equipos': [{'nombre': eq['nombre'], 'puntos': eq['puntos'], 'faltas': eq['faltas']}
                        for eq in self.equipos],
            'timer': {'restante': self.tiempo_restante, 'corriendo': self.corriendo},
            'sonidos': [{'nombre': s['name'], 'cargado': s['obj'] is not None} for s in self.sonidos],
        }

    def bombear_comandos_remotos(self):
        """Ejecuta en el hilo de Tkinter los comandos que llegaron por la red."""
        if self.remoto and self.remoto.activo:
            for comando in self.remoto.vaciar_comandos():
                try: self.aplicar_comando_remoto(comando)
                except Exception as e: print(f"Comando remoto ignorado ({comando}): {e}")
        self.root.after(REMOTE_POLL_MS, self.bombear_comandos_remotos)

    def aplicar_comando_remoto(self, cmd):
        """Traduce un comando del celular a la acción equivalente del panel."""
        accion = cmd.get('accion')

        if accion in ('puntos', 'faltas'):
            idx = int(cmd.get('equipo', -1))
            delta = 1 if int(cmd.get('delta', 1)) >= 0 else -1
            if 0 <= idx < len(self.equipos):
                self.mod(idx, delta, 'p' if accion == 'puntos' else 'f')

        elif accion == 'timer_start': self.iniciar_tiempo()
        elif accion == 'timer_pause': self.pausar_tiempo()
        elif accion == 'timer_set':
            segundos = max(0, min(int(cmd.get('segundos', 0)), 99 * 60 + 59))
            self.tiempo_restante = segundos
            # Reflejamos el cambio en las casillas del panel para no descuadrar al operador.
            self.e_min.delete(0, "end"); self.e_min.insert(0, str(segundos // 60))
            self.e_sec.delete(0, "end"); self.e_sec.insert(0, f"{segundos % 60:02d}")
            self.redibujar_pantalla()

        elif accion == 'sonido':
            slot = int(cmd.get('slot', -1))
            if 0 <= slot < len(self.sonidos): self.play_sound(slot)

if __name__ == "__main__":
    ImproMatchApp()