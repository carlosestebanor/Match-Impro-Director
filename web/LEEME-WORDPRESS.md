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

## Opción A · Subir la carpeta y enlazarla (la más simple)

1. Entra al **hPanel de Hostinger → Archivos → Administrador de archivos**.
2. Abre `public_html`.
3. Crea una carpeta llamada `tablero`.
4. Sube dentro el contenido de esta carpeta `web/`, manteniendo la estructura:

   ```
   public_html/tablero/
     ├── index.html
     ├── tablero.html
     ├── css/estilos.css
     └── js/estado.js, tablero.js, panel.js, almacen.js
   ```

5. Ya está disponible en **https://accionimpro.com.co/tablero/**

6. En WordPress, añade el enlace donde quieras (menú, botón, entrada de blog).

> **Importante:** sube los archivos tal cual, sin renombrar carpetas. El panel
> carga los `.js` por ruta relativa y abre `tablero.html` desde la misma carpeta.

---

## Opción B · Una página de WordPress que lo contenga

Si prefieres que la barra de navegación del sitio siga visible:

1. Haz primero la Opción A.
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
`/tablero/` como alternativa. Por eso recomendamos la Opción A como principal
y el iframe solo como vitrina.

---

## Requisitos del servidor

Ninguno especial, pero conviene comprobar:

- **HTTPS activo.** Hostinger lo da gratis con Let's Encrypt. Hace falta para
  que funcionen la pantalla completa y el guardado en el navegador.
- **Tipo MIME de los `.js`.** Apache lo sirve bien por defecto. Si el navegador
  se queja de que el módulo no carga, añade esto a `public_html/tablero/.htaccess`:

  ```apache
  AddType application/javascript .js
  ```

- **Caché.** Para que la página cargue instantáneamente en visitas siguientes,
  el mismo `.htaccess` puede llevar:

  ```apache
  <IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType text/css "access plus 7 days"
    ExpiresByType application/javascript "access plus 7 days"
    ExpiresByType text/html "access plus 1 hour"
  </IfModule>
  ```

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
