# Publicar el tablero web en accionimpro.com.co

Guía para poner la versión web en el sitio de WordPress alojado en Hostinger.

La aplicación es **HTML, CSS y JavaScript planos**: no necesita PHP, ni base de
datos, ni Node, ni ningún plugin. Se sube como un archivo más y funciona.

---

## Qué es esta versión

| | Escritorio (Windows) | Web (navegador) |
| :--- | :--- | :--- |
| Instalación | Descargar el ZIP | Ninguna, se abre un enlace |
| Tablero en el proyector | Ventana aparte | Ventana aparte (igual) |
| Cronómetro, puntos, faltas | ✅ | ✅ |
| Efectos de sonido | ✅ | ✅ |
| Fondo y logo propios | ✅ | ✅ |
| Diseño personalizable | ✅ | ✅ |
| Presets `.json` | ✅ | ✅ **compatibles entre ambas** |
| Mando desde el celular | ✅ (WiFi local) | ❌ *(ver «Fase 2» al final)* |
| Funciona sin internet | ✅ | ✅ una vez cargada la página |

Los datos del operador (equipos, diseño, imágenes, sonidos) se guardan **en su
propio navegador**. No viajan a ningún servidor, así que no hay que gestionar
privacidad de usuarios ni cumplir con nada especial.

---

## Opción A · Con un solo comando (recomendada si tienes SSH)

En la carpeta `web/` hay dos scripts listos. Se ejecutan **desde tu computador**,
no desde el servidor.

1. Saca los datos de conexión en **hPanel → Avanzado → Acceso SSH** y expórtalos:

   ```bash
   export HOSTINGER_USUARIO=u123456789
   export HOSTINGER_SERVIDOR=193.203.xxx.xxx
   export HOSTINGER_PUERTO=65002
   export HOSTINGER_DESTINO=domains/accionimpro.com.co/public_html/tablero
   ```

2. Haz primero un **simulacro**: enseña exactamente qué subiría, sin tocar nada.

   ```bash
   cd web
   ./desplegar.sh
   ```

3. Si la lista te cuadra, súbelo de verdad:

   ```bash
   ./desplegar.sh --aplicar
   ```

4. Comprueba que todo quedó bien publicado:

   ```bash
   ./verificar.sh https://accionimpro.com.co/tablero/
   ```

El script solo sincroniza los 8 archivos de la aplicación y **se niega a
ejecutarse si la ruta de destino apunta a `public_html`**: usa `rsync --delete`,
así que apuntar a la raíz borraría WordPress entero.

> **Nota sobre Claude Code:** si le pides el despliegue a una sesión que corre
> **en tu computador** (la CLI o la app de escritorio), puede ejecutar estos
> mismos pasos por ti, porque ahí sí ve tus claves SSH. Una sesión en la nube
> (Claude Code web) corre en un contenedor aislado, sin acceso a tu `~/.ssh`
> ni salida por el puerto 22, así que no puede desplegar.

---

## Opción B · Subir la carpeta a mano (sin terminal)

Genera primero el paquete:

```bash
cd web && ./desplegar.sh --empaquetar     # crea tablero-web.zip (~68 KB)
```

1. Entra al **hPanel de Hostinger → Archivos → Administrador de archivos**.
2. Abre `public_html`.
3. Crea una carpeta llamada `tablero`.
4. Sube el ZIP dentro, usa **«Extraer»** y borra después el ZIP del servidor.
   Debe quedar así:

   ```
   public_html/tablero/
     ├── index.html
     ├── tablero.html
     ├── .htaccess
     ├── css/estilos.css
     └── js/estado.js, tablero.js, panel.js, almacen.js
   ```

5. Ya está disponible en **https://accionimpro.com.co/tablero/**

6. En WordPress, añade el enlace donde quieras (menú, botón, entrada de blog).

> El `.htaccess` incluido ya trae el tipo MIME de los `.js`, la compresión y la
> caché. Si tu administrador de archivos oculta los archivos que empiezan por
> punto, activa «Mostrar archivos ocultos» antes de subirlo.

> **Importante:** sube los archivos tal cual, sin renombrar carpetas. El panel
> carga los `.js` por ruta relativa y abre `tablero.html` desde la misma carpeta.

---

## Opción C · Una página de WordPress que lo contenga

Si prefieres que la barra de navegación del sitio siga visible:

1. Haz primero la Opción A o B.
2. Crea una página nueva en WordPress (por ejemplo «Tablero de Match»).
3. Añade un bloque **HTML personalizado** con:

   ```html
   <iframe src="/tablero/index.html"
           style="width:100%;height:90vh;border:0;border-radius:12px"
           title="Match Impro Director"
           allow="fullscreen"></iframe>
   ```

4. Publica.

**Advertencia:** dentro de un `iframe`, algunos navegadores bloquean la ventana
emergente del tablero. Si ocurre, deja también visible el enlace directo a
`/tablero/` como alternativa. Por eso recomendamos la Opción A o B como principal
y el iframe solo como vitrina.

---

## Requisitos del servidor

Ninguno especial, pero conviene comprobar:

- **HTTPS activo.** Hostinger lo da gratis con Let's Encrypt. Hace falta para
  que funcionen la pantalla completa y el guardado en el navegador.
- **Tipo MIME, compresión y caché.** Ya vienen resueltos en el `.htaccess` que
  se sube con la aplicación. Solo asegúrate de que ese archivo llegue al
  servidor: empieza por punto y algunos gestores de archivos lo ocultan.

---

## Para que traiga tráfico

- **Imagen de portada.** Sube un `portada.png` (1200×630 px) a la misma carpeta:
  es la que se ve al compartir el enlace en WhatsApp, Facebook o Instagram.
  Ya está declarada en `index.html`.
- **Revisa las URL** de las etiquetas `og:url` y `canonical` en `index.html` si
  cambias la ruta `/tablero/`.
- **Escribe una entrada** explicando la herramienta y enlazando al tablero: es
  lo que posiciona en buscadores, no la aplicación en sí.
- **Pon el crédito visible.** La pestaña «Ayuda» ya enlaza a accionimpro.com.co;
  cada compañía que la use verá de dónde salió.
- **Ofrece las dos versiones** en la misma página: la web para probar al
  instante, y el `.exe` para quien quiera el mando por WiFi.

---

## Fase 2 (opcional): mando desde el celular

Es lo único que la versión web no hace hoy. En la de escritorio funciona porque
el programa levanta un pequeño servidor en la red local; una página web no puede
hacer eso.

Sí es viable en Hostinger, y **sin WebSockets ni Node**: el mando actual ya
funciona por sondeo HTTP cada segundo, así que basta con un par de scripts PHP
que hagan de buzón compartido:

```
public_html/tablero/api/
  estado.php    → guarda y devuelve el estado de una «sala» (código de 6 cifras)
  comando.php   → recibe las órdenes del celular y las deja en cola
```

El panel del operador publicaría su estado cada segundo y leería la cola; el
celular haría lo contrario. Requiere:

- Un código de sala + PIN (igual que ahora) para que nadie ajeno entre.
- Borrado automático de las salas inactivas (una tarea programada de Hostinger).
- Tener en cuenta que el tráfico pasaría por el servidor: si se corta internet
  en el teatro, el mando deja de funcionar. La versión de escritorio no depende
  de internet, solo del WiFi local.

Es una tarde de trabajo, pero conviene decidirlo aparte: cambia la aplicación de
«todo en el navegador del usuario» a «con servicio propio», y eso implica
mantenimiento y responsabilidad sobre datos de terceros.

---

## Compatibilidad de presets

Un archivo `.json` guardado en la versión de escritorio se abre en la web y al
revés: mismos equipos, colores, diseño y tiempos.

La única diferencia son las **rutas de archivos**. El escritorio guarda
`C:\fx\buzzer.wav`; el navegador no puede abrir esa ruta, así que el efecto
aparece con su nombre pero sin sonido hasta que se vuelva a cargar el archivo.
Lo mismo con el fondo y el logo. Los nombres, colores, tiempos y ajustes de
diseño se conservan íntegros.

---

*Corporación Acción Impro · Medellín, Colombia · 2026 · Licencia CC BY 4.0*
