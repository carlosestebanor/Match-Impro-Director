---
🌍 **Idiomas / Languages:** [Castellano] | [English](README_EN.md)
---

# 🎭 Match Impro Director - Ultimate Edition

![Acción Impro](https://img.shields.io/badge/Developed%20by-Acción%20Impro-blue)
![License](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey)
![Version](https://img.shields.io/badge/Version-1.0.0--stable-green)

Software profesional de dirección técnica diseñado específicamente para **Match de Improvisación**, competencias teatrales y eventos de artes escénicas en vivo. Desarrollado en Medellín, Colombia, por la **Corporación Acción Impro**.

## 📸 Vista Previa

| Tablero del Público | Panel de Control |
| :---: | :---: |
| ![Tablero](boardliveview.png) | ![Panel](controlpanelboard.png) |

## ✨ Características Principales

- **Doble Pantalla (Multimonitor):** Controla todo desde tu laptop mientras el público ve solo el tablero profesional en el proyector.
- **Fullscreen Inteligente:** Soporte tipo navegador (F11) y doble clic para expandir el tablero exactamente en el monitor auxiliar.
- **Diseño Adaptable:** Cambia fondos (16:9, 4:3, 1:1), carga logos personalizados y ajusta la posición de cada elemento con precisión milimétrica.
- **Control en Vivo:** Edita nombres de equipos, suma puntos y gestiona faltas (máximo 3 con estilo semáforo) sin pausar el show.
- **Soundbar Integrada:** Lanzador de 6 slots de efectos de sonido (MP3/WAV) con nombres personalizables.
- **Cronómetro Flexible:** Reloj con cuenta regresiva que puedes ubicar arriba o abajo y ocultar según la dinámica del match.
- **Control Remoto por WiFi:** Maneja puntos, faltas, cronómetro y efectos desde el celular o la tablet, sin quedarte pegado al computador.

## 📡 Control Remoto (Mando por WiFi)

Permite que un asistente (o tú mismo desde la sala) opere el marcador desde el navegador de un celular. No requiere instalar nada en el teléfono ni salir a internet: todo ocurre dentro de tu red local.

1. Conecta el computador y el celular a la **misma red WiFi**.
2. En el panel de control abre la pestaña **📡 REMOTO** y presiona **ENCENDER**.
3. Escribe en el navegador del celular la dirección que aparece (por ejemplo `http://192.168.1.20:8770`).
4. Ingresa el **PIN** de 6 dígitos que muestra el panel. El celular lo recuerda para las siguientes veces.

Desde el mando puedes sumar/restar puntos, marcar y quitar faltas, fijar el cronómetro, dar inicio/pausa y lanzar los 6 efectos de sonido. El tablero del proyector se actualiza al instante.

**Recomendaciones de seguridad**
- Cualquier persona conectada a esa red puede llegar a la página del mando; por eso está protegido con PIN.
- En redes públicas o compartidas, genera un **PIN nuevo** antes de la función con el botón 🔄.
- Apaga el servidor al terminar el show.
- Si Windows pregunta por el Firewall la primera vez, permite el acceso en **redes privadas**.
- Si el puerto 8770 está ocupado, cámbialo en la misma pestaña (por ejemplo 8771).

## 🚀 Instalación y Uso

### Para Usuarios (Ejecutable)
1. Descarga el archivo `MatchDirector_ByAccionImpro.zip` desde la sección de **Releases**.
2. Conecta tu proyector o segunda pantalla en modo "Extender".
3. Abre la aplicación y arrastra la ventana del "Tablero Público" a la pantalla del público.
4. Haz **doble clic** sobre el tablero o presiona **F11** para ponerlo en pantalla completa.

### Para Programadores (Código Fuente)
El código está escrito en **Python 3.12**.
1. Clona el repositorio.
2. Instala las dependencias: `pip install pillow pygame`
3. Ejecuta el script principal: `python match_director_source.py`

> El control remoto vive en `remote_control.py` y usa **solo la librería estándar** (no añade dependencias). Mantén ese archivo junto a `match_director_source.py`; si falta, el programa arranca igual pero la pestaña 📡 REMOTO queda deshabilitada.

## 🎨 Personalización
En la pestaña **DISEÑO** puedes:
- Cambiar colores de nombres, puntos y faltas.
- Seleccionar tipografías del sistema.
- Ajustar márgenes (padding) y redondez de los contenedores.
- Activar/Desactivar visibilidad de elementos para "Match Amistosos".

## 📜 Licencia y Créditos

Este software se distribuye bajo la licencia **Creative Commons Atribución 4.0 Internacional (CC BY 4.0)**.

**Atribución:**
Desarrollado por la **Corporación Acción Impro**, Medellín, Colombia, 2026.
[https://accionimpro.com.co/](https://accionimpro.com.co/)

---
*Hecho por y para improvisadores.* 🎭

