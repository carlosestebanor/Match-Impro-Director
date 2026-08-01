# Historial de cambios

Todas las novedades relevantes de **Match Impro Director**.

---

## [2.2.0] — 2026

### 🌐 Versión web

- **Nueva versión para navegador** en `web/`: panel del operador y ventana de
  tablero, escritos en HTML/CSS/JS sin dependencias ni servidor. Pensada para
  publicarla en un sitio web y que cualquier compañía la use sin instalar nada.
- **Mismo motor de dibujo y mismas proporciones** que la versión de escritorio.
- **Presets `.json` intercambiables** entre ambas versiones. Una prueba
  automática comprueba que los campos no se desincronicen.
- **Todo se guarda en el navegador** (equipos, diseño, fondo, logo y efectos,
  estos últimos en IndexedDB). Nada se envía a ningún servidor.
- Guía de publicación en WordPress/Hostinger: `web/LEEME-WORDPRESS.md`.
- El mando por WiFi desde el celular sigue siendo exclusivo del escritorio:
  una página web no puede abrir un servidor en la red local.

### 🐛 Correcciones

- En el modelo JavaScript, los campos decimales del diseño se truncaban a
  entero: `Number.isInteger(1.0)` es `true` en JavaScript, así que el truco de
  deducir el tipo a partir del valor por defecto —válido en Python— dejaba el
  zoom, los tamaños y los offsets sin decimales. Ahora las claves enteras se
  declaran explícitamente.

---

## [2.1.0] — 2026

Versión centrada en la experiencia de uso durante la función.

### 🎛 Panel del operador

- **Vista previa en vivo del tablero.** Una miniatura muestra exactamente lo que
  está viendo el público. Antes, con el tablero a pantalla completa en el
  proyector, el operador tenía que girarse para comprobar qué se proyectaba.
  Un clic en la miniatura activa la pantalla completa.
- **Semáforo de faltas en el panel.** Cada equipo muestra sus faltas junto a los
  botones. Antes ese dato solo existía en la proyección.
- **Jerarquía visual.** El marcador y los botones de puntos —lo que más se pulsa
  en una noche— crecen y ganan área táctil; el reloj del panel es más grande.
- **Contraste accesible.** Los grises de texto pasan el mínimo AA (4,5:1). Los de
  la versión anterior llegaban a 2,1:1 sobre su fondo: ilegibles en sala oscura.
- **Barra de estado legible**, con color según la importancia del aviso
  (confirmación, alerta o error).
- **La acción destructiva se separa.** «Reiniciar» pasa al extremo opuesto de
  «Deshacer» para que un clic errado no borre el marcador.

### 📱 Mando a distancia

- **La pantalla del celular ya no se apaga** durante la función (Wake Lock).
- **Acuse de recibo al pulsar:** el botón destella cuando el panel confirma la
  orden, y vibra al tocarlo. En una sala ruidosa no había forma de saber si el
  toque había llegado.

### ⚡ Coste

La miniatura añade 2,6 ms al redibujado completo y 0,4 ms al segundo de reloj.
Se puede desactivar con la casilla «Mostrar» en equipos muy justos de CPU.

---

## [2.0.0] — 2026

Versión centrada en el rendimiento, la fiabilidad en función y la comodidad del operador.

### ⚡ Rendimiento

- **Caché de imágenes en el tablero.** El fondo y el logo se reescalan solo cuando
  cambia el tamaño de la ventana. Antes se reescalaban en *cada* redibujado.
- **Actualización incremental del cronómetro.** Cada segundo se reescribe únicamente
  el texto del reloj en vez de reconstruir el tablero completo.
- **Redibujado agrupado.** Diez cambios seguidos (sliders, ráfaga de comandos del
  celular) producen un solo repintado, no diez.
- **Reescalado en dos tiempos.** Al arrastrar la ventana se usa un filtro rápido y,
  al soltar, se refina en alta calidad.

Medido en la misma máquina, con fondo Full HD y logo:

| Operación | v1.0 | v2.0 |
| :--- | ---: | ---: |
| Redibujado completo (mediana) | 63,9 ms | 3,9 ms |
| Segundo de cronómetro | 63,9 ms | 0,10 ms |

### 🐛 Correcciones

- **El cronómetro ya no se atrasa.** Antes restaba un segundo por cada ciclo de
  dibujo, así que acumulaba el retraso de cada repintado; en un match largo se
  separaba varios segundos del tiempo real. Ahora se calcula contra el reloj
  del sistema y no acumula deriva.
- **Los botones de efectos ya no se quedan encendidos.** Al pulsar dos veces
  seguidas, el botón guardaba su propio color de destello como color base y
  quedaba en cian para siempre.
- **Pantalla completa en cualquier sistema.** Se usa el modo nativo de Tk en vez
  de un truco que solo funcionaba en Windows.
- **Imágenes dañadas o ausentes.** Ya no tumban el tablero: se avisa y el
  marcador se sigue dibujando. Tampoco se reintenta abrirlas en bucle.
- **Cancelar el diálogo de fondo** ya no descartaba la imagen en uso.
- **Tiempos inválidos.** Escribir letras o `88` segundos ahora avisa en lugar de
  ignorarse en silencio.
- **Cierre limpio.** Al salir se cancelan los temporizadores pendientes; antes
  Tk imprimía errores en la consola.

### ✨ Novedades

- **Guardado automático.** Diseño, equipos, colores, volumen y rutas de efectos
  se recuperan al abrir el programa.
- **Presets por espectáculo.** Exporta e importa configuraciones completas (`.json`).
- **Deshacer y rehacer** puntos y faltas (`Ctrl+Z` / `Ctrl+Y`). Un punto mal dado
  ya no obliga a recalcular a mano.
- **Atajos de teclado** para operar sin soltar el ratón (ver pestaña ❔ AYUDA).
- **Color por equipo**, con una franja identificativa en el tablero.
- **Hasta 6 equipos** (antes 4).
- **Alerta de tiempo:** el reloj cambia de color en los segundos finales, con
  umbral configurable.
- **Reloj grande en el panel**, para no depender de mirar al proyector.
- **Ajustes rápidos de tiempo** (±10 s y ±30 s) en el panel y en el celular.
- **Control de volumen** y botón de silencio para los efectos.
- **Quitar fondo** y **vaciar un slot de sonido**.
- **Reiniciar marcador** con confirmación.
- **Barra de estado** que informa de cada acción.
- **Pestaña de ayuda** con los atajos y la ruta del archivo de preferencias.
- **Mando a distancia ampliado:** deshacer, ajustes rápidos de tiempo, silenciar
  y colores de equipo.

### 🧱 Estructura

El programa se dividió en módulos con responsabilidades claras:

| Archivo | Contenido |
| :--- | :--- |
| `match_director_source.py` | Panel del operador |
| `match_state.py` | Datos del partido, cronómetro y guardado |
| `tablero.py` | Motor de dibujo de la proyección |
| `remote_control.py` | Mando a distancia por WiFi |
| `pruebas/` | 152 pruebas automáticas |

---

## [1.1.0] — 2026

### ✨ Novedades

- **Control remoto por WiFi.** Servidor web integrado para manejar el marcador
  desde el navegador de un celular o tablet, protegido con PIN.

---

## [1.0.0] — 2026

Primera versión estable.

- Tablero para proyector en ventana independiente, con fondo y logo propios.
- Cronómetro con cuenta regresiva.
- De 2 a 4 equipos con puntos y faltas (máximo 3, estilo semáforo).
- Seis efectos de sonido con nombres personalizables.
- Personalización de colores, tipografías, posiciones y visibilidad.
