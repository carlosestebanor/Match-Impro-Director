# Historial de cambios

Todas las novedades relevantes de **Match Impro Director**.

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
