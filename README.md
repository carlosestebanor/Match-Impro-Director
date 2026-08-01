---
🌍 **Idiomas / Languages:** [Castellano] | [English](README_EN.md)
---

# 🎭 Match Impro Director - Ultimate Edition

![Acción Impro](https://img.shields.io/badge/Developed%20by-Acción%20Impro-blue)
![License](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey)
![Version](https://img.shields.io/badge/Version-2.1.0--stable-green)
![Pruebas](https://img.shields.io/badge/Pruebas-169%20automáticas-brightgreen)

Software profesional de dirección técnica diseñado específicamente para **Match de Improvisación**, competencias teatrales y eventos de artes escénicas en vivo. Desarrollado en Medellín, Colombia, por la **Corporación Acción Impro**.

## 📸 Vista Previa

| Tablero del Público | Panel de Control |
| :---: | :---: |
| ![Tablero](boardliveview.png) | ![Panel](controlpanelboard.png) |

## ✨ Características Principales

- **Doble Pantalla (Multimonitor):** Controla todo desde tu laptop mientras el público ve solo el tablero profesional en el proyector.
- **Fullscreen Inteligente:** Pantalla completa nativa (F11 o doble clic) en el monitor donde esté el tablero. Funciona en Windows, Linux y macOS.
- **Diseño Adaptable:** Cambia fondos (16:9, 4:3, 1:1), carga logos personalizados y ajusta la posición de cada elemento con precisión milimétrica.
- **Vista Previa en Vivo:** Una miniatura en el panel te muestra exactamente lo que ve el público, sin girarte hacia el proyector.
- **Control en Vivo:** Edita nombres, suma puntos y gestiona faltas (máximo 3 con estilo semáforo) sin pausar el show. Hasta **6 equipos**, cada uno con su color.
- **Deshacer y Rehacer:** Un punto mal asignado se corrige con `Ctrl+Z`, no recalculando a mano.
- **Soundbar Integrada:** Lanzador de 6 slots de efectos (MP3/WAV/OGG) con nombres personalizables, control de volumen y botón de silencio.
- **Cronómetro Preciso:** Cuenta regresiva sin deriva, ubicable arriba o abajo, con ajustes rápidos (±10 s, ±30 s) y alerta de color en los segundos finales.
- **Control Remoto por WiFi:** Maneja todo desde el celular o la tablet, sin quedarte pegado al computador.
- **Todo se Guarda Solo:** Diseño, equipos, colores y efectos se recuperan al abrir el programa. Además puedes exportar un preset por espectáculo.

## 🚀 Instalación y Uso

### Para Usuarios (Ejecutable)
1. Descarga el archivo `MatchDirector_ByAccionImpro.zip` desde la sección de **Releases**.
2. Conecta tu proyector o segunda pantalla en modo "Extender".
3. Abre la aplicación y arrastra la ventana del "Tablero Público" a la pantalla del público.
4. Haz **doble clic** sobre el tablero o presiona **F11** para ponerlo en pantalla completa.

### Para Programadores (Código Fuente)
El código está escrito en **Python 3.10 o superior** (probado en 3.11 y 3.12).

```bash
git clone https://github.com/carlosestebanor/Match-Impro-Director.git
cd Match-Impro-Director
pip install -r requirements.txt
python match_director_source.py
```

## ⌨️ Atajos de Teclado

Pensados para operar con una mano mientras la otra maneja el sonido. Se ignoran mientras escribes en una casilla de texto.

| Tecla | Acción |
| :--- | :--- |
| `Espacio` | Inicia o pausa el cronómetro |
| `1` … `6` | Suma un punto al equipo N |
| `Shift` + `1` … `6` | Resta un punto al equipo N |
| `F1` … `F6` | Marca una falta al equipo N |
| `Ctrl` + `Z` / `Ctrl` + `Y` | Deshacer / rehacer una jugada |
| `Ctrl` + `S` | Guardar las preferencias ahora |
| `Ctrl` + `R` | Reiniciar el marcador |
| `F11` o doble clic | Pantalla completa del tablero |
| `Esc` | Salir de pantalla completa |

## 📡 Control Remoto (Mando por WiFi)

Permite que un asistente (o tú mismo desde la sala) opere el marcador desde el navegador de un celular. No requiere instalar nada en el teléfono ni salir a internet: todo ocurre dentro de tu red local.

1. Conecta el computador y el celular a la **misma red WiFi**.
2. En el panel de control abre la pestaña **📡 REMOTO** y presiona **ENCENDER**.
3. Escribe en el navegador del celular la dirección que aparece (por ejemplo `http://192.168.1.20:8770`).
4. Ingresa el **PIN** de 6 dígitos que muestra el panel. El celular lo recuerda para las siguientes veces.

Desde el mando puedes sumar y restar puntos, marcar y quitar faltas, fijar y ajustar el cronómetro, deshacer la última jugada, lanzar los 6 efectos y silenciarlos. El tablero del proyector se actualiza al instante.

**Recomendaciones de seguridad**
- Cualquier persona conectada a esa red puede llegar a la página del mando; por eso está protegido con PIN.
- En redes públicas o compartidas, genera un **PIN nuevo** antes de la función con el botón 🔄.
- Apaga el servidor al terminar el show.
- Si Windows pregunta por el Firewall la primera vez, permite el acceso en **redes privadas**.
- Si el puerto 8770 está ocupado, cámbialo en la misma pestaña (por ejemplo 8771).

## 💾 Preferencias y Presets

El programa guarda solo tu configuración (diseño, equipos, colores, volumen y rutas de los efectos) y la recupera al abrir. La ruta exacta del archivo aparece en la pestaña **❔ AYUDA**:

- Junto al programa, si la carpeta admite escritura — así los presets viajan contigo en el USB.
- Si no, en tu carpeta personal (`~/.match_impro_director/`).

Con **💾 Guardar** y **📂 Cargar** puedes exportar un preset distinto por espectáculo o por compañía.

## 🎨 Personalización
En la pestaña **DISEÑO** puedes:
- Cambiar colores de nombres, puntos, faltas, cajas, reloj y alerta.
- Seleccionar tipografías del sistema.
- Ajustar márgenes (padding), redondez de los contenedores y posiciones.
- Activar/Desactivar visibilidad de elementos para "Match Amistosos".

## 🧱 Estructura del Proyecto

| Archivo | Contenido |
| :--- | :--- |
| `match_director_source.py` | Panel del operador (interfaz) |
| `match_state.py` | Datos del partido, cronómetro y guardado |
| `tablero.py` | Motor de dibujo de la proyección |
| `remote_control.py` | Mando a distancia por WiFi |
| `pruebas/` | Pruebas automáticas |

Los tres últimos módulos deben viajar junto al principal. Si falta `remote_control.py`, el programa arranca igual y solo se deshabilita la pestaña 📡 REMOTO.

## 🧪 Pruebas

```bash
python pruebas/ejecutar.py            # todo
python pruebas/ejecutar.py --sin-gui  # solo lo que no necesita pantalla
```

En Linux sin escritorio: `xvfb-run -a python pruebas/ejecutar.py`.

## ⚡ Rendimiento

La versión 2.0 reescribió el motor de dibujo. Medido con fondo Full HD y logo en la misma máquina:

| Operación | v1.0 | v2.0 |
| :--- | ---: | ---: |
| Redibujado completo (mediana) | 63,9 ms | 3,9 ms |
| Segundo de cronómetro | 63,9 ms | 0,10 ms |

Consulta el [historial de cambios](CHANGELOG.md) para el detalle completo.

## 📜 Licencia y Créditos

Este software se distribuye bajo la licencia **Creative Commons Atribución 4.0 Internacional (CC BY 4.0)**. Ver [LICENSE](LICENSE).

**Atribución:**
Desarrollado por la **Corporación Acción Impro**, Medellín, Colombia, 2026.
[https://accionimpro.com.co/](https://accionimpro.com.co/)

---
*Hecho por y para improvisadores.* 🎭
