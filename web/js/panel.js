/*
 * MATCH IMPRO DIRECTOR :: PANEL DEL OPERADOR (versión web)
 * ---------------------------------------------------------------------------
 * Equivalente de `match_director_source.py`. Une el modelo, el motor de dibujo
 * y el almacén local, y sincroniza la ventana del tablero.
 *
 * Corporación Acción Impro · Medellín, Colombia · 2026 · CC BY 4.0
 */

import {
  EstadoPartido, DISENO_POR_DEFECTO, CLAVES_ENTERAS,
  MAX_EQUIPOS, MIN_EQUIPOS, MAX_FALTAS, NUM_SONIDOS, TIEMPO_MAXIMO,
} from './estado.js';
import { dibujarTablero, prepararLienzo } from './tablero.js';
import * as almacen from './almacen.js';

const $ = (sel) => document.querySelector(sel);
const canal = new BroadcastChannel('match-impro-director');
const estado = new EstadoPartido(3);

/* Recursos vivos: URLs de objeto + audio ya preparado */
const medios = { fondo: null, logo: null };     // { nombre, url }
const imagenes = { fondo: null, logo: null };   // HTMLImageElement
const audios = new Array(NUM_SONIDOS).fill(null);

let ventanaTablero = null;
let tableroAbierto = false;
let idGuardado = null;
let ultimoSegundo = null;

const FUENTES = ['Arial', 'Impact', 'Georgia', 'Verdana', 'Tahoma', 'Trebuchet MS',
  'Times New Roman', 'Courier New', 'Bebas Neue', 'Oswald', 'system-ui'];

const SLIDERS = [
  ['offset_global_y', 'Pos. vertical', -0.5, 0.5, 0.01],
  ['offset_x', 'Pos. horizontal', -0.3, 0.3, 0.01],
  ['offset_names', 'Offset nombres', -0.2, 0.2, 0.01],
  ['offset_scores', 'Offset puntos', -0.2, 0.2, 0.01],
  ['offset_timer', 'Ajuste reloj', -0.5, 0.5, 0.01],
  ['name_scale', 'Tam. nombres', 0.5, 3, 0.1],
  ['scale_factor', 'Zoom general', 0.5, 2, 0.05],
  ['box_padding', 'Margen cajas', 0.5, 2, 0.05],
  ['corner_radius', 'Redondez cajas', 0, 60, 1],
  ['logo_scale', 'Tam. logo', 0.1, 2, 0.05],
  ['logo_offset_y', 'Pos. Y logo', -0.5, 0.5, 0.01],
];

/* ========================================================================== */
/* AVISOS                                                                     */
/* ========================================================================== */
function avisar(mensaje, tipo = 'info') {
  const barra = $('#estado');
  barra.textContent = mensaje;
  barra.className = tipo === 'info' ? '' : tipo;
}

/* ========================================================================== */
/* ARRANQUE                                                                   */
/* ========================================================================== */
async function iniciar() {
  const guardado = almacen.leerConfig();
  if (guardado) {
    try { estado.aplicarDict(guardado); }
    catch { avisar('Las preferencias guardadas estaban dañadas; se usan las de fábrica.', 'alerta'); }
  }

  construirSelectorEquipos();
  construirSliders();
  construirFuentes();
  construirEfectos();
  conectarEventos();
  await restaurarMedios();

  sincronizarControlesDiseno();
  construirEquipos();
  refrescarTodo();

  setInterval(tic, 100);
  avisar('Listo. Pulsa «Abrir tablero» y arrastra la ventana al proyector.');
}

/* ========================================================================== */
/* CONSTRUCCIÓN DE LA INTERFAZ                                                */
/* ========================================================================== */
function construirSelectorEquipos() {
  const sel = $('#num-equipos');
  sel.innerHTML = '';
  for (let n = MIN_EQUIPOS; n <= MAX_EQUIPOS; n++) {
    const op = document.createElement('option');
    op.value = op.textContent = n;
    sel.appendChild(op);
  }
  sel.value = estado.equipos.length;
}

function construirEquipos() {
  const cont = $('#equipos');
  cont.innerHTML = '';
  estado.equipos.forEach((equipo, i) => {
    const fila = document.createElement('div');
    fila.className = 'equipo';
    fila.style.borderLeftColor = equipo.color;
    fila.innerHTML = `
      <div class="cabecera">
        <span class="indice">${i + 1}</span>
        <input type="color" data-color-equipo="${i}" aria-label="Color del equipo ${i + 1}">
        <input type="text" data-nombre="${i}" maxlength="40" aria-label="Nombre del equipo ${i + 1}">
      </div>
      <div class="controles">
        <button class="btn-punto" data-punto="${i}" data-delta="-1" aria-label="Restar punto">−</button>
        <span class="puntos" data-puntos="${i}">0</span>
        <button class="btn-punto" data-punto="${i}" data-delta="1" aria-label="Sumar punto">+</button>
        <span class="luces" data-luces="${i}">${'<span class="luz"></span>'.repeat(MAX_FALTAS)}</span>
        <button class="btn-quitar-falta" data-falta="${i}" data-delta="-1">quitar</button>
        <button class="btn-falta" data-falta="${i}" data-delta="1">FALTA</button>
      </div>`;
    fila.querySelector(`[data-color-equipo="${i}"]`).value = aHex(equipo.color);
    fila.querySelector(`[data-nombre="${i}"]`).value = equipo.nombre;
    cont.appendChild(fila);
  });
  refrescarMarcador();
}

function construirEfectos() {
  const rejilla = $('#rejilla-fx');
  const config = $('#config-fx');
  rejilla.innerHTML = '';
  config.innerHTML = '';

  estado.sonidos.forEach((ranura, i) => {
    const boton = document.createElement('button');
    boton.dataset.fx = i;
    boton.textContent = ranura.nombre;
    boton.disabled = true;
    rejilla.appendChild(boton);

    const fila = document.createElement('div');
    fila.className = 'fila';
    fila.style.marginBottom = '6px';
    fila.innerHTML = `
      <span style="color:var(--texto-tenue);font-size:11px;width:18px">#${i + 1}</span>
      <input type="text" data-nombre-fx="${i}" maxlength="24" class="crece" aria-label="Nombre del efecto ${i + 1}">
      <button data-cargar-fx="${i}">📂</button>
      <button data-vaciar-fx="${i}">✖</button>`;
    fila.querySelector(`[data-nombre-fx="${i}"]`).value = ranura.nombre;
    config.appendChild(fila);
  });
}

function construirSliders() {
  const cont = $('#sliders');
  cont.innerHTML = '';
  SLIDERS.forEach(([clave, etiqueta, min, max, paso]) => {
    const campo = document.createElement('div');
    campo.className = 'campo';
    campo.innerHTML = `
      <label for="sl-${clave}">${etiqueta}</label>
      <input type="range" id="sl-${clave}" data-slider="${clave}"
             min="${min}" max="${max}" step="${paso}">
      <span class="valor" data-valor="${clave}"></span>`;
    cont.appendChild(campo);
  });
}

function construirFuentes() {
  [['#f-nombres', 'font_family'], ['#f-puntos', 'font_score']].forEach(([sel, clave]) => {
    const select = $(sel);
    select.innerHTML = '';
    FUENTES.forEach(f => {
      const op = document.createElement('option');
      op.value = op.textContent = f;
      select.appendChild(op);
    });
    select.dataset.fuente = clave;
  });
}

/* ========================================================================== */
/* EVENTOS                                                                    */
/* ========================================================================== */
function conectarEventos() {
  // --- Barra superior ---
  $('#btn-deshacer').onclick = () => { if (estado.deshacer()) { refrescarTodo(); avisar('Jugada deshecha.'); } };
  $('#btn-rehacer').onclick = () => { if (estado.rehacer()) { refrescarTodo(); avisar('Jugada rehecha.'); } };
  // (refrescarTodo ya repinta el marcador, ver más abajo)
  $('#btn-reiniciar').onclick = reiniciarMarcador;
  $('#btn-exportar').onclick = exportarPreset;
  $('#btn-importar').onclick = () => $('#entrada-preset').click();
  $('#btn-tablero').onclick = abrirTablero;
  $('#lienzo-previa').onclick = abrirTablero;

  // --- Cronómetro ---
  $('#btn-set').onclick = fijarTiempo;
  $('#btn-inicio').onclick = () => {
    if (estado.cronometro.iniciar()) { avisar('Cronómetro en marcha.', 'ok'); refrescarTodo(); }
    else if (estado.cronometro.restante === 0) avisar('Fija un tiempo antes de iniciar (botón SET).', 'error');
  };
  $('#btn-pausa').onclick = () => {
    if (estado.cronometro.pausar()) { avisar('Cronómetro en pausa.', 'alerta'); refrescarTodo(); }
  };
  document.querySelectorAll('[data-ajuste]').forEach(b => {
    b.onclick = () => {
      estado.cronometro.ajustar(Number(b.dataset.ajuste));
      sincronizarEntradasTiempo();
      refrescarTodo();
    };
  });

  // --- Equipos (delegación) ---
  $('#num-equipos').onchange = (e) => {
    estado.ajustarNumeroEquipos(Number(e.target.value));
    e.target.value = estado.equipos.length;
    construirEquipos();
    refrescarTodo();
    programarGuardado();
  };

  $('#equipos').addEventListener('click', (e) => {
    const punto = e.target.closest('[data-punto]');
    if (punto) return accionMarcador(Number(punto.dataset.punto), Number(punto.dataset.delta), 'p');
    const falta = e.target.closest('[data-falta]');
    if (falta) return accionMarcador(Number(falta.dataset.falta), Number(falta.dataset.delta), 'f');
  });

  $('#equipos').addEventListener('input', (e) => {
    const nombre = e.target.closest('[data-nombre]');
    if (nombre) {
      estado.renombrar(Number(nombre.dataset.nombre), nombre.value);
      refrescarTodo(); programarGuardado(); return;
    }
    const color = e.target.closest('[data-color-equipo]');
    if (color) {
      const i = Number(color.dataset.colorEquipo);
      estado.pintarEquipo(i, color.value);
      color.closest('.equipo').style.borderLeftColor = color.value;
      refrescarTodo(); refrescarMarcador(); programarGuardado();
    }
  });

  // --- Efectos ---
  $('#rejilla-fx').addEventListener('click', (e) => {
    const b = e.target.closest('[data-fx]');
    if (b) reproducir(Number(b.dataset.fx));
  });
  $('#config-fx').addEventListener('click', (e) => {
    const cargar = e.target.closest('[data-cargar-fx]');
    if (cargar) return pedirArchivo('#entrada-audio', f => cargarEfecto(Number(cargar.dataset.cargarFx), f));
    const vaciar = e.target.closest('[data-vaciar-fx]');
    if (vaciar) return vaciarEfecto(Number(vaciar.dataset.vaciarFx));
  });
  $('#config-fx').addEventListener('input', (e) => {
    const campo = e.target.closest('[data-nombre-fx]');
    if (!campo) return;
    const i = Number(campo.dataset.nombreFx);
    estado.sonidos[i].nombre = campo.value.slice(0, 24);
    $(`[data-fx="${i}"]`).textContent = estado.sonidos[i].nombre;
    programarGuardado();
  });
  $('#volumen').oninput = (e) => {
    estado.volumen = Number(e.target.value) / 100;
    audios.forEach(a => { if (a) a.volume = estado.volumen; });
    programarGuardado();
  };
  $('#btn-silenciar').onclick = () => {
    audios.forEach(a => { if (a) { a.pause(); a.currentTime = 0; } });
    avisar('Efectos detenidos.');
  };

  // --- Diseño ---
  document.querySelectorAll('[data-flag]').forEach(chk => {
    chk.onchange = () => {
      estado.diseno[chk.dataset.flag] = chk.checked;
      refrescarTodo(); programarGuardado();
    };
  });
  document.querySelectorAll('[data-color]').forEach(inp => {
    inp.oninput = () => {
      estado.diseno[inp.dataset.color] = inp.value;
      refrescarTodo(); refrescarMarcador(); programarGuardado();
    };
  });
  $('#sliders').addEventListener('input', (e) => {
    const sl = e.target.closest('[data-slider]');
    if (!sl) return;
    const clave = sl.dataset.slider;
    const valor = Number(sl.value);
    estado.diseno[clave] = CLAVES_ENTERAS.has(clave) ? Math.trunc(valor) : valor;
    $(`[data-valor="${clave}"]`).textContent = formatear(estado.diseno[clave], clave);
    refrescarTodo(); programarGuardado();
  });
  $('#pos-timer').onchange = (e) => {
    estado.diseno.timer_position = e.target.value;
    refrescarTodo(); programarGuardado();
  };
  $('#seg-alerta').oninput = (e) => {
    const n = Number(e.target.value);
    if (Number.isFinite(n)) { estado.diseno.segundos_alerta = Math.max(0, Math.trunc(n)); refrescarTodo(); programarGuardado(); }
  };
  [['#f-nombres'], ['#f-puntos']].forEach(([sel]) => {
    $(sel).onchange = (e) => {
      estado.diseno[e.target.dataset.fuente] = e.target.value;
      refrescarTodo(); programarGuardado();
    };
  });
  $('#btn-fondo').onclick = () => pedirArchivo('#entrada-imagen', f => cargarImagen('fondo', f));
  $('#btn-logo').onclick = () => pedirArchivo('#entrada-imagen', f => cargarImagen('logo', f));
  $('#btn-quitar-fondo').onclick = () => quitarImagen('fondo');
  $('#btn-quitar-logo').onclick = () => quitarImagen('logo');
  $('#btn-restablecer').onclick = restablecerDiseno;
  $('#btn-borrar-datos').onclick = borrarTodo;

  // --- Pestañas ---
  document.querySelectorAll('.pestanas button').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('.pestanas button').forEach(o => {
        o.setAttribute('aria-selected', String(o === b));
        $('#' + o.dataset.panel).hidden = o !== b;
      });
    };
  });

  // --- Vista previa ---
  $('#chk-previa').onchange = () => {
    $('#lienzo-previa').hidden = !$('#chk-previa').checked;
    pintarPrevia();
  };

  // --- Preset ---
  $('#entrada-preset').onchange = (e) => {
    const archivo = e.target.files[0];
    e.target.value = '';
    if (archivo) importarPreset(archivo);
  };

  // --- Teclado ---
  document.addEventListener('keydown', atajos);

  // --- Canal con la ventana del tablero ---
  canal.onmessage = (evento) => {
    const m = evento.data;
    if (!m) return;
    if (m.tipo === 'tablero-listo') { marcarTablero(true); enviarEstado(); }
    if (m.tipo === 'tablero-cerrado') marcarTablero(false);
  };

  window.addEventListener('resize', pintarPrevia);
  window.addEventListener('beforeunload', () => { guardar(); canal.postMessage({ tipo: 'cerrar' }); });
}

/* ========================================================================== */
/* ACCIONES DEL MARCADOR                                                      */
/* ========================================================================== */
function accionMarcador(i, delta, tipo) {
  const cambiado = tipo === 'p' ? estado.sumarPuntos(i, delta) : estado.sumarFaltas(i, delta);
  if (!cambiado) return;
  refrescarMarcador();
  refrescarTodo();
}

function reiniciarMarcador() {
  if (!confirm('¿Poner en cero los puntos y las faltas de todos los equipos?\n\nLos nombres y el diseño se conservan.')) return;
  estado.reiniciarMarcador();
  sincronizarEntradasTiempo();
  refrescarMarcador();
  refrescarTodo();
  avisar('Marcador reiniciado.', 'ok');
}

function fijarTiempo() {
  const min = Number($('#min').value);
  const seg = Number($('#seg').value);
  if (!Number.isFinite(min) || !Number.isFinite(seg)) {
    return avisar('Minutos y segundos deben ser números.', 'error');
  }
  if (min < 0 || seg < 0 || seg > 59) {
    return avisar('Revisa el tiempo: los segundos van de 0 a 59.', 'error');
  }
  estado.cronometro.fijar(Math.min(min * 60 + seg, TIEMPO_MAXIMO));
  sincronizarEntradasTiempo();
  refrescarTodo();
  programarGuardado();
}

function sincronizarEntradasTiempo() {
  const s = estado.cronometro.restante;
  $('#min').value = Math.floor(s / 60);
  $('#seg').value = s % 60;
}

/* ========================================================================== */
/* BUCLE DEL RELOJ                                                            */
/* ========================================================================== */
function tic() {
  if (estado.cronometro.revisarAgotado()) {
    avisar('⏰ ¡TIEMPO! Se acabó la cuenta regresiva.', 'alerta');
  }
  const segundo = estado.cronometro.restante;
  if (segundo !== ultimoSegundo) {
    ultimoSegundo = segundo;
    refrescarTodo();
  }
}

/* ========================================================================== */
/* REFRESCO                                                                   */
/* ========================================================================== */
function refrescarTodo() {
  const crono = estado.cronometro;
  const reloj = $('#reloj');
  reloj.textContent = crono.texto();
  reloj.className = crono.restante <= estado.diseno.segundos_alerta ? 'alerta'
    : (crono.corriendo ? 'corriendo' : '');
  $('#btn-deshacer').disabled = !estado.puedeDeshacer;
  $('#btn-rehacer').disabled = !estado.puedeRehacer;
  refrescarMarcador();
  pintarPrevia();
  enviarEstado();
}

function refrescarMarcador() {
  estado.equipos.forEach((equipo, i) => {
    const puntos = $(`[data-puntos="${i}"]`);
    if (puntos) puntos.textContent = equipo.puntos;
    const luces = $(`[data-luces="${i}"]`);
    if (luces) {
      [...luces.children].forEach((luz, k) => {
        luz.style.background = k < equipo.faltas ? estado.diseno.color_faltas : '#555';
      });
    }
  });
}

function pintarPrevia() {
  const lienzo = $('#lienzo-previa');
  if (!$('#chk-previa').checked || !lienzo.clientWidth) return;
  const [ancho, alto, ctx] = prepararLienzo(lienzo);
  dibujarTablero(ctx, ancho, alto, estado.instantanea(), imagenes);
}

function enviarEstado() {
  const inst = estado.instantanea();
  inst.diseno.fondo_path = medios.fondo ? medios.fondo.url : '';
  inst.diseno.logo_path = medios.logo ? medios.logo.url : '';
  canal.postMessage({ tipo: 'estado', datos: inst });
}

function sincronizarControlesDiseno() {
  const d = estado.diseno;
  document.querySelectorAll('[data-flag]').forEach(c => { c.checked = Boolean(d[c.dataset.flag]); });
  document.querySelectorAll('[data-color]').forEach(c => { c.value = aHex(d[c.dataset.color]); });
  document.querySelectorAll('[data-slider]').forEach(s => {
    s.value = d[s.dataset.slider];
    $(`[data-valor="${s.dataset.slider}"]`).textContent = formatear(d[s.dataset.slider], s.dataset.slider);
  });
  $('#pos-timer').value = d.timer_position;
  $('#seg-alerta').value = d.segundos_alerta;
  $('#f-nombres').value = FUENTES.includes(d.font_family) ? d.font_family : 'Arial';
  $('#f-puntos').value = FUENTES.includes(d.font_score) ? d.font_score : 'Impact';
  $('#volumen').value = Math.round(estado.volumen * 100);
  $('#num-equipos').value = estado.equipos.length;
  sincronizarEntradasTiempo();
}

/* ========================================================================== */
/* VENTANA DEL TABLERO                                                        */
/* ========================================================================== */
function abrirTablero() {
  if (ventanaTablero && !ventanaTablero.closed) {
    ventanaTablero.focus();
    return;
  }
  ventanaTablero = window.open('tablero.html', 'tableroMatchImpro',
    'width=960,height=540,menubar=no,toolbar=no,location=no');
  if (!ventanaTablero) {
    avisar('El navegador bloqueó la ventana emergente. Permítela para este sitio y vuelve a intentarlo.', 'error');
    return;
  }
  avisar('Tablero abierto: arrástralo al proyector y pulsa F11.', 'ok');
}

function marcarTablero(abierto) {
  tableroAbierto = abierto;
  $('#aviso-tablero').textContent = abierto
    ? '✅ Tablero abierto y sincronizado.'
    : 'El tablero aún no está abierto.';
}

/* ========================================================================== */
/* MEDIOS (imágenes y sonidos)                                                */
/* ========================================================================== */
function pedirArchivo(selector, alElegir) {
  const entrada = $(selector);
  entrada.onchange = () => {
    const archivo = entrada.files[0];
    entrada.value = '';
    if (archivo) alElegir(archivo);
  };
  entrada.click();
}

async function cargarImagen(clave, archivo) {
  if (!archivo.type.startsWith('image/')) {
    return avisar('Ese archivo no es una imagen.', 'error');
  }
  await almacen.guardarMedio(clave, archivo);
  aplicarImagen(clave, URL.createObjectURL(archivo), archivo.name);
  programarGuardado();
  avisar(`${clave === 'fondo' ? 'Fondo' : 'Logo'}: ${archivo.name}`, 'ok');
}

function aplicarImagen(clave, url, nombre) {
  if (medios[clave]) URL.revokeObjectURL(medios[clave].url);
  medios[clave] = { url, nombre };
  const img = new Image();
  img.onload = () => { imagenes[clave] = img; refrescarTodo(); };
  img.onerror = () => { imagenes[clave] = null; avisar('No se pudo abrir esa imagen.', 'error'); };
  img.src = url;
}

async function quitarImagen(clave) {
  if (medios[clave]) URL.revokeObjectURL(medios[clave].url);
  medios[clave] = null;
  imagenes[clave] = null;
  await almacen.borrarMedio(clave);
  refrescarTodo();
  programarGuardado();
}

async function cargarEfecto(i, archivo) {
  const clave = `fx${i}`;
  await almacen.guardarMedio(clave, archivo);
  estado.sonidos[i].path = archivo.name;
  aplicarAudio(i, URL.createObjectURL(archivo));
  programarGuardado();
  avisar(`FX ${i + 1}: ${archivo.name}`, 'ok');
}

function aplicarAudio(i, url) {
  if (audios[i]) URL.revokeObjectURL(audios[i].src);
  const audio = new Audio(url);
  audio.volume = estado.volumen;
  audio.preload = 'auto';
  audios[i] = audio;
  const boton = $(`[data-fx="${i}"]`);
  if (boton) boton.disabled = false;
}

async function vaciarEfecto(i) {
  if (audios[i]) { audios[i].pause(); URL.revokeObjectURL(audios[i].src); }
  audios[i] = null;
  estado.sonidos[i].path = '';
  await almacen.borrarMedio(`fx${i}`);
  const boton = $(`[data-fx="${i}"]`);
  if (boton) boton.disabled = true;
  programarGuardado();
}

function reproducir(i) {
  const audio = audios[i];
  if (!audio) return avisar(`El botón #${i + 1} no tiene ningún efecto cargado.`, 'error');
  audio.currentTime = 0;
  audio.play().catch(() => avisar('El navegador bloqueó el audio. Toca la página una vez.', 'error'));
  const boton = $(`[data-fx="${i}"]`);
  boton.classList.add('sonando');
  setTimeout(() => boton.classList.remove('sonando'), 200);
}

async function restaurarMedios() {
  for (const clave of ['fondo', 'logo']) {
    const registro = await almacen.leerMedio(clave);
    if (registro) aplicarImagen(clave, URL.createObjectURL(registro.blob), registro.nombre);
  }
  for (let i = 0; i < NUM_SONIDOS; i++) {
    const registro = await almacen.leerMedio(`fx${i}`);
    if (registro) aplicarAudio(i, URL.createObjectURL(registro.blob));
  }
}

/* ========================================================================== */
/* PREFERENCIAS Y PRESETS                                                     */
/* ========================================================================== */
function instantaneaGuardable() {
  const datos = estado.aDict();
  // En el navegador no existen rutas de archivo: guardamos el nombre a título
  // informativo. El contenido real vive en IndexedDB.
  datos.diseno.fondo_path = medios.fondo ? medios.fondo.nombre : '';
  datos.diseno.logo_path = medios.logo ? medios.logo.nombre : '';
  return datos;
}

function programarGuardado() {
  clearTimeout(idGuardado);
  idGuardado = setTimeout(guardar, 800);
}

function guardar() {
  if (!almacen.guardarConfig(instantaneaGuardable())) {
    avisar('No se pudieron guardar las preferencias en este navegador.', 'error');
  }
}

function exportarPreset() {
  const blob = new Blob([JSON.stringify(instantaneaGuardable(), null, 2)],
    { type: 'application/json' });
  const enlace = document.createElement('a');
  enlace.href = URL.createObjectURL(blob);
  enlace.download = 'preset_match.json';
  enlace.click();
  setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
  avisar('Preset descargado.', 'ok');
}

async function importarPreset(archivo) {
  try {
    estado.aplicarDict(JSON.parse(await archivo.text()));
  } catch (e) {
    return avisar(`No se pudo leer el preset: ${e.message}`, 'error');
  }
  construirSelectorEquipos();
  construirEquipos();
  construirEfectos();
  await restaurarMedios();
  sincronizarControlesDiseno();
  estado.sonidos.forEach((s, i) => {
    const boton = $(`[data-fx="${i}"]`);
    if (boton) { boton.textContent = s.nombre; boton.disabled = !audios[i]; }
  });
  refrescarTodo();
  guardar();
  avisar(`Preset cargado: ${archivo.name}`, 'ok');
}

function restablecerDiseno() {
  if (!confirm('¿Volver al diseño por defecto?\n\nSe conservan los equipos, el marcador y los sonidos.')) return;
  Object.assign(estado.diseno, DISENO_POR_DEFECTO);
  sincronizarControlesDiseno();
  refrescarTodo();
  programarGuardado();
  avisar('Diseño restablecido.', 'ok');
}

async function borrarTodo() {
  if (!confirm('Se borrarán equipos, diseño, fondo, logo y efectos guardados en este navegador.\n\n¿Continuar?')) return;
  almacen.borrarConfig();
  await Promise.all(['fondo', 'logo', ...Array.from({ length: NUM_SONIDOS }, (_, i) => `fx${i}`)]
    .map(almacen.borrarMedio));
  location.reload();
}

/* ========================================================================== */
/* ATAJOS DE TECLADO                                                          */
/* ========================================================================== */
function atajos(e) {
  const escribiendo = ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName);

  if (e.ctrlKey || e.metaKey) {
    const tecla = e.key.toLowerCase();
    if (tecla === 'z') { e.preventDefault(); if (estado.deshacer()) { refrescarTodo(); refrescarMarcador(); } return; }
    if (tecla === 'y') { e.preventDefault(); if (estado.rehacer()) { refrescarTodo(); refrescarMarcador(); } return; }
    if (tecla === 's') { e.preventDefault(); exportarPreset(); return; }
    return;
  }

  // F1..F6 marcan falta y funcionan siempre (no se confunden con escribir)
  const falta = /^F([1-6])$/.exec(e.key);
  if (falta) { e.preventDefault(); accionMarcador(Number(falta[1]) - 1, 1, 'f'); return; }

  if (escribiendo) return;

  if (e.code === 'Space') {
    e.preventDefault();
    estado.cronometro.alternar();
    refrescarTodo();
    return;
  }
  if (/^[1-6]$/.test(e.key)) {
    e.preventDefault();
    accionMarcador(Number(e.key) - 1, e.shiftKey ? -1 : 1, 'p');
  }
}

/* ========================================================================== */
/* UTILIDADES                                                                 */
/* ========================================================================== */
function formatear(valor, clave) {
  // Ojo: Number.isInteger(1.0) es true en JavaScript, así que el formato se
  // decide por la clave, no por el valor.
  return CLAVES_ENTERAS.has(clave) ? String(Math.trunc(valor)) : Number(valor).toFixed(2);
}

/** Los <input type="color"> solo aceptan #rrggbb. */
function aHex(color) {
  const texto = String(color || '').trim();
  if (/^#[0-9a-f]{6}$/i.test(texto)) return texto.toLowerCase();
  if (/^#[0-9a-f]{3}$/i.test(texto)) {
    return '#' + texto.slice(1).split('').map(c => c + c).join('').toLowerCase();
  }
  return '#000000';
}

// Sin este `catch`, un fallo durante el arranque dejaría medio panel sin
// conectar y sin ninguna pista de lo ocurrido.
iniciar().catch((e) => {
  console.error('Fallo al iniciar el panel:', e);
  avisar(`No se pudo iniciar el panel: ${e.message}`, 'error');
});
