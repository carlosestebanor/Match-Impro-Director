/*
 * MATCH IMPRO DIRECTOR :: MOTOR DE DIBUJO DEL TABLERO (versión web)
 * ---------------------------------------------------------------------------
 * Equivalente de `tablero.py` sobre Canvas 2D. Usa las mismas proporciones que
 * la versión de escritorio, así que un diseño ajustado allí se ve igual aquí.
 *
 * Corporación Acción Impro · Medellín, Colombia · 2026 · CC BY 4.0
 */

const MAX_FALTAS = 3;

/** Color del reloj: normal, o de alerta en los segundos finales. */
export function colorTimer(inst) {
  const d = inst.diseno;
  return inst.timer.restante <= d.segundos_alerta ? d.color_alerta : d.color_timer;
}

function cajaRedondeada(ctx, x, y, w, h, radio) {
  radio = Math.max(0, Math.min(radio, Math.abs(w) / 2, Math.abs(h) / 2));
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, radio);
  else {
    // Respaldo para navegadores sin roundRect
    ctx.moveTo(x + radio, y);
    ctx.arcTo(x + w, y, x + w, y + h, radio);
    ctx.arcTo(x + w, y + h, x, y + h, radio);
    ctx.arcTo(x, y + h, x, y, radio);
    ctx.arcTo(x, y, x + w, y, radio);
    ctx.closePath();
  }
  ctx.fill();
}

/** Parte el nombre en líneas para que quepa en el ancho de su columna. */
function envolverTexto(ctx, texto, anchoMax) {
  const palabras = String(texto).split(/\s+/).filter(Boolean);
  if (!palabras.length) return [''];
  const lineas = [];
  let actual = palabras[0];
  for (let i = 1; i < palabras.length; i++) {
    const prueba = actual + ' ' + palabras[i];
    if (ctx.measureText(prueba).width <= anchoMax) actual = prueba;
    else { lineas.push(actual); actual = palabras[i]; }
  }
  lineas.push(actual);
  return lineas;
}

/**
 * Dibuja el tablero completo.
 *
 * @param ctx       contexto 2D ya escalado a píxeles CSS
 * @param ancho     ancho en píxeles CSS
 * @param alto      alto en píxeles CSS
 * @param inst      instantánea del estado (equipos, diseño, timer)
 * @param recursos  { fondo: HTMLImageElement|null, logo: HTMLImageElement|null }
 */
export function dibujarTablero(ctx, ancho, alto, inst, recursos = {}) {
  const d = inst.diseno;
  ctx.clearRect(0, 0, ancho, alto);
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, ancho, alto);
  if (ancho < 10 || alto < 10) return;

  // 1. Fondo (se estira a la ventana, como en la versión de escritorio)
  if (recursos.fondo && recursos.fondo.complete && recursos.fondo.naturalWidth) {
    ctx.drawImage(recursos.fondo, 0, 0, ancho, alto);
  }

  // 2. Logo
  const logo = recursos.logo;
  if (logo && logo.complete && logo.naturalHeight) {
    const altoLogo = alto * 0.2 * d.logo_scale;
    const anchoLogo = altoLogo * (logo.naturalWidth / logo.naturalHeight);
    const lx = ancho * 0.5 - anchoLogo / 2;
    const ly = alto * 0.5 + alto * d.logo_offset_y - altoLogo / 2;
    ctx.drawImage(logo, lx, ly, anchoLogo, altoLogo);
  }

  // 3. Medidas base (idénticas a tablero.py)
  const fuenteBase = Math.max(8, alto * 0.05 * d.scale_factor);
  const grosorBorde = Math.max(2, fuenteBase * 0.06);
  const cx = ancho * 0.5 + ancho * d.offset_x;
  const cyEquipos = alto * 0.5 + alto * d.offset_global_y;
  let cyTimer = (d.timer_position === 'Arriba' ? alto * 0.15 : alto * 0.85);
  cyTimer += alto * d.offset_timer;

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';

  // 4. Cronómetro
  if (d.ver_timer) {
    const tw = ancho * 0.25 * d.scale_factor * d.box_padding;
    const th = alto * 0.15 * d.scale_factor * d.box_padding;
    ctx.fillStyle = d.color_caja;
    cajaRedondeada(ctx, cx - tw / 2, cyTimer - th / 2, tw, th, d.corner_radius);
    ctx.font = `${Math.round(fuenteBase * 2.5)}px ${d.font_score}, Impact, sans-serif`;
    ctx.fillStyle = colorTimer(inst);
    ctx.fillText(textoTimer(inst.timer.restante), cx, cyTimer);
  }

  // 5. Equipos
  const equipos = inst.equipos;
  if (!equipos.length) return;
  const colW = ancho / equipos.length;

  equipos.forEach((equipo, i) => {
    const x = i * colW + colW / 2 + ancho * d.offset_x;
    const yNombre = cyEquipos - alto * 0.12 + alto * d.offset_names;
    const yPuntos = cyEquipos + alto * 0.02 + alto * d.offset_scores;

    // Nombre (con envoltura y contorno negro opcional)
    const tamNombre = Math.round(fuenteBase * d.name_scale);
    ctx.font = `bold ${tamNombre}px ${d.font_family}, Arial, sans-serif`;
    const lineas = envolverTexto(ctx, equipo.nombre, colW * 0.9);
    const altoLinea = tamNombre * 1.12;
    const yPrimera = yNombre - ((lineas.length - 1) * altoLinea) / 2;

    lineas.forEach((linea, k) => {
      const y = yPrimera + k * altoLinea;
      if (d.ver_outline) {
        ctx.lineWidth = grosorBorde * 2;
        ctx.strokeStyle = '#000';
        ctx.strokeText(linea, x, y);
      }
      ctx.fillStyle = d.color_nombres;
      ctx.fillText(linea, x, y);
    });

    // Franja con el color del equipo, encima del bloque de texto
    if (d.ver_barra_color) {
      const barraW = colW * 0.42 * d.scale_factor;
      const barraH = Math.max(3, alto * 0.012 * d.scale_factor);
      const tope = yPrimera - altoLinea / 2;
      const yBarra = tope - barraH - Math.max(2, alto * 0.012);
      ctx.fillStyle = equipo.color;
      cajaRedondeada(ctx, x - barraW / 2, yBarra, barraW, barraH, barraH / 2);
    }

    // Puntos
    const pw = alto * 0.2 * d.scale_factor * d.box_padding;
    const ph = pw * 0.8;
    ctx.fillStyle = d.color_caja;
    cajaRedondeada(ctx, x - pw / 2, yPuntos - ph / 2, pw, ph, d.corner_radius);
    ctx.font = `${Math.round(fuenteBase * 3)}px ${d.font_score}, Impact, sans-serif`;
    ctx.fillStyle = d.color_puntos;
    ctx.fillText(String(equipo.puntos), x, yPuntos);

    // Faltas (semáforo)
    if (d.ver_faltas) {
      const yFaltas = yPuntos + alto * 0.16;
      const fw = pw, fh = ph * 0.4;
      ctx.fillStyle = d.color_caja;
      cajaRedondeada(ctx, x - fw / 2, yFaltas - fh / 2, fw, fh, d.corner_radius);
      const r = fh * 0.3;
      const hueco = r * 0.5;
      const inicio = x - (r * 2 * MAX_FALTAS + hueco * (MAX_FALTAS - 1)) / 2 + r;
      for (let k = 0; k < MAX_FALTAS; k++) {
        ctx.beginPath();
        ctx.arc(inicio + k * (r * 2 + hueco), yFaltas, r, 0, Math.PI * 2);
        ctx.fillStyle = k < equipo.faltas ? d.color_faltas : '#333333';
        ctx.fill();
      }
    }
  });
}

export function textoTimer(segundos) {
  return String(Math.floor(segundos / 60)).padStart(2, '0') + ':' +
         String(segundos % 60).padStart(2, '0');
}

/**
 * Ajusta el lienzo a su tamaño real en pantalla teniendo en cuenta la densidad
 * de píxeles: sin esto, en pantallas HiDPI el tablero se ve borroso.
 * Devuelve [ancho, alto] en píxeles CSS.
 */
export function prepararLienzo(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const ancho = canvas.clientWidth;
  const alto = canvas.clientHeight;
  if (canvas.width !== Math.round(ancho * dpr) || canvas.height !== Math.round(alto * dpr)) {
    canvas.width = Math.round(ancho * dpr);
    canvas.height = Math.round(alto * dpr);
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return [ancho, alto, ctx];
}
