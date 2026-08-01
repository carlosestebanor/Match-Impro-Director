# Publicar el tablero en tu web · Paso a paso

Guía para dejar el tablero funcionando en **accionimpro.com.co/tablero/**.

**No necesitas programar ni usar la terminal.** Solo el navegador.
Tiempo estimado: 10 minutos.

---

## Antes de empezar

Solo necesitas dos cosas:

- Tu usuario y contraseña de **Hostinger** (hpanel.hostinger.com).
- Un computador con navegador.

Nada de esto toca tu WordPress. Vamos a crear una carpeta nueva **al lado** de
tu web actual. Si algo sale mal, se borra la carpeta y todo queda como estaba.

---

## PARTE 1 · Descargar el archivo (2 minutos)

### Paso 1
Entra a esta dirección en tu navegador:

```
https://github.com/carlosestebanor/Match-Impro-Director/blob/claude/remote-control-8x4ktl/tablero-web.zip
```

### Paso 2
Verás una página de GitHub con el nombre del archivo. Busca el botón de
descarga (un icono de flecha hacia abajo ⬇, arriba a la derecha del recuadro)
y haz clic.

### Paso 3
Se descargará **`tablero-web.zip`** a tu carpeta de Descargas.
Pesa 24 KB (es muy pequeño, tarda un segundo).

> **No lo descomprimas.** Lo vas a subir tal cual, comprimido.

---

## PARTE 2 · Subirlo a Hostinger (5 minutos)

### Paso 4
Entra a **https://hpanel.hostinger.com** e inicia sesión.

### Paso 5
Verás la lista de tus sitios web. Haz clic en **accionimpro.com.co**.

### Paso 6
En el menú de la izquierda busca **Archivos** y dentro
**Administrador de archivos**. Haz clic.

*Se abrirá algo parecido al explorador de tu computador, con carpetas.*

### Paso 7
Busca y abre la carpeta **`public_html`** (doble clic).

*Esa es la carpeta donde vive tu web. Verás dentro archivos de WordPress
como `wp-admin`, `wp-content`, `wp-config.php`. **No toques nada de eso.***

### Paso 8
Crea una carpeta nueva:

- Busca el botón **«Nueva carpeta»** o el icono de carpeta con un **+**
  (suele estar arriba a la izquierda).
- Escribe exactamente: **`tablero`** (todo en minúsculas, sin acentos).
- Confirma.

### Paso 9
Entra en la carpeta `tablero` que acabas de crear (doble clic).
Debe estar vacía.

### Paso 10
Sube el archivo:

- Busca el botón **«Subir archivos»** o el icono de flecha hacia arriba ⬆.
- Selecciona el `tablero-web.zip` que descargaste en el Paso 3.
- Espera a que termine (es instantáneo, pesa muy poco).

### Paso 11
Descomprímelo **en el servidor**:

- Haz clic derecho sobre `tablero-web.zip`.
- Elige **«Extraer»** (o *Extract*).
- Si te pregunta dónde, deja la ruta que sale por defecto y acepta.

*Ahora deberías ver estas cosas dentro de la carpeta `tablero`:*

```
index.html
tablero.html
css      (carpeta)
js       (carpeta)
```

*Puede que también veas `.htaccess`. Es normal y debe estar ahí.*

### Paso 12
Borra el ZIP del servidor: clic derecho sobre `tablero-web.zip` → **Eliminar**.
Ya no hace falta y así no queda a la vista de nadie.

---

## PARTE 3 · Comprobar que funciona (3 minutos)

### Paso 13
Abre una pestaña nueva del navegador y entra a:

```
https://accionimpro.com.co/tablero/
```

**Debes ver** un panel oscuro con el título «MATCH IMPRO DIRECTOR», un
cronómetro grande en 04:00 y tres equipos (ROJO, AMARILLO, AZUL).

✅ Si lo ves: **ya está publicado**. Sigue al Paso 14 para la prueba final.

❌ Si ves un error, salta al apartado «Si algo no salió bien» del final.

### Paso 14
Haz la prueba de verdad, como en una función:

1. Pulsa el botón **🖥 Abrir tablero** (arriba a la derecha).
   Se abre una ventana nueva y negra: eso es lo que verá el público.
2. Si el navegador dice que bloqueó una ventana emergente, dale a
   **«Permitir»** y vuelve a pulsar el botón.
3. En el panel, pulsa el **+** de un equipo. El número debe subir **también**
   en la ventana negra.
4. En la ventana negra, pulsa **F11**: se pone a pantalla completa.
   Con **Esc** vuelve a la normalidad.

Si eso funciona, está todo correcto.

---

## PARTE 4 · Enlazarlo desde tu web (2 minutos)

Para que la gente lo encuentre:

### Paso 15
Entra al panel de WordPress (`accionimpro.com.co/wp-admin`).

### Paso 16
Ve a **Apariencia → Menús** y añade un enlace personalizado:

- **URL:** `https://accionimpro.com.co/tablero/`
- **Texto del enlace:** `Tablero de Match` (o como prefieras)

### Paso 17
Guarda el menú. Listo: ya aparece en la navegación de tu web.

---

## Si algo no salió bien

### Veo un error 404 o «Página no encontrada»
La carpeta no se llama exactamente `tablero`, o no está dentro de
`public_html`. Vuelve al Paso 7 y comprueba la ruta:
`public_html` → `tablero` → `index.html`.

### Veo una lista de archivos en vez del panel
Falta el `index.html` dentro de `tablero`, o el ZIP se extrajo en una carpeta
de más (por ejemplo `tablero/tablero-web/index.html`). Mueve los archivos un
nivel hacia arriba.

### La página se ve en blanco o a medias
Casi seguro faltan las carpetas `css` y `js`. Comprueba que el ZIP se extrajo
completo (Paso 11) y que dentro de `js` hay cuatro archivos.

### Sale el aviso «El navegador bloqueó la ventana emergente»
Es normal la primera vez. En la barra de direcciones aparece un icono para
permitir ventanas emergentes de tu sitio. Acéptalo y vuelve a pulsar
**🖥 Abrir tablero**.

### Me sale el diseño de WordPress en vez del panel
Muy raro, pero si pasa, avísame: haría falta ajustar el `.htaccess`.

---

## Opcional · La imagen para compartir

Cuando compartas el enlace por WhatsApp o Instagram, se muestra una tarjeta
con una imagen. Para que salga tu imagen y no un recuadro vacío:

1. Prepara una imagen de **1200 × 630 píxeles** (puede ser una captura del
   tablero con el logo de Acción Impro).
2. Nómbrala exactamente **`portada.png`**.
3. Súbela a la carpeta `tablero` del servidor (mismo sitio que `index.html`).

---

## Cuando quieras actualizarlo

Si más adelante cambia el tablero, repite la Parte 1 y la Parte 2: descarga el
ZIP nuevo, súbelo a la misma carpeta y extrae sobreescribiendo. No hace falta
borrar nada primero.

---

*Corporación Acción Impro · Medellín, Colombia · 2026 · Licencia CC BY 4.0*
