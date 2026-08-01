/*
 * MATCH IMPRO DIRECTOR :: MODELO DE DATOS (versión web)
 * ---------------------------------------------------------------------------
 * Equivalente en JavaScript de `match_state.py`. Guarda y lee EXACTAMENTE el
 * mismo formato JSON que la versión de escritorio, así que un preset guardado
 * en el programa de Windows se puede cargar aquí y al revés.
 *
 * Corporación Acción Impro · Medellín, Colombia · 2026 · CC BY 4.0
 */

export const MAX_FALTAS = 3;
export const MAX_EQUIPOS = 6;
export const MIN_EQUIPOS = 2;
export const NUM_SONIDOS = 6;
export const TIEMPO_MAXIMO = 99 * 60 + 59;
const PROFUNDIDAD_DESHACER = 60;

const EQUIPOS_POR_DEFECTO = [
  ['ROJO', '#e02020'], ['AMARILLO', '#f2c500'], ['AZUL', '#1f6feb'],
  ['VERDE', '#2ea043'], ['BLANCO', '#e6e6e6'], ['NEGRO', '#4a4a4a'],
];

/*
 * Claves del diseño que SÍ son números enteros.
 *
 * Hay que declararlas a mano: en JavaScript no existe la distinción entre
 * entero y decimal, así que `Number.isInteger(1.0)` devuelve true y no se
 * puede deducir el tipo a partir del valor por defecto (a diferencia de
 * Python, donde 1.0 es float). Sin esta lista, un zoom de 1,5 se truncaría
 * a 1 y los sliders decimales quedarían inservibles.
 */
export const CLAVES_ENTERAS = new Set(['corner_radius', 'segundos_alerta']);

export const DISENO_POR_DEFECTO = {
  scale_factor: 1.0, name_scale: 1.0,
  offset_global_y: 0.0, offset_names: 0.0, offset_scores: 0.0,
  offset_timer: 0.0, offset_x: 0.0,
  logo_scale: 0.5, logo_offset_y: -0.4,
  font_family: 'Arial', font_score: 'Impact',
  color_nombres: '#ffffff', color_puntos: '#ffcc00', color_faltas: '#ff0000',
  color_caja: '#000000', color_timer: '#ffffff', color_alerta: '#ff3b30',
  box_padding: 1.0, corner_radius: 20,
  timer_position: 'Abajo',
  ver_timer: true, ver_faltas: true, ver_outline: true, ver_barra_color: true,
  segundos_alerta: 10,
  fondo_path: '', logo_path: '',
};

/* ========================================================================== */
/* CRONÓMETRO                                                                 */
/* ========================================================================== */
export class Cronometro {
  constructor(duracion = 240, ahora = () => performance.now() / 1000) {
    this._ahora = ahora;
    this.duracion = Math.trunc(duracion);
    this._restante = duracion;
    this._fin = null;
  }

  get corriendo() { return this._fin !== null; }

  get restante() {
    const crudo = this._fin === null ? this._restante : this._fin - this._ahora();
    if (crudo <= 0) return 0;
    // Techo, como un reloj de pared: 04:00 durante el primer segundo.
    return Math.min(TIEMPO_MAXIMO, Math.ceil(crudo));
  }

  get agotado() { return this.restante === 0; }

  texto() {
    const s = this.restante;
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }

  fijar(segundos) {
    segundos = Math.max(0, Math.min(Math.trunc(segundos) || 0, TIEMPO_MAXIMO));
    this.duracion = segundos;
    if (this.corriendo) this._fin = this._ahora() + segundos;
    else this._restante = segundos;
    return segundos;
  }

  ajustar(delta) { return this.fijar(this.restante + Math.trunc(delta)); }

  iniciar() {
    if (this.corriendo || this.restante <= 0) return false;
    this._fin = this._ahora() + this._restante;
    return true;
  }

  pausar() {
    if (!this.corriendo) return false;
    this._restante = Math.max(0, this._fin - this._ahora());
    this._fin = null;
    return true;
  }

  alternar() { return this.corriendo ? this.pausar() : this.iniciar(); }

  reiniciar() { this._fin = null; this._restante = this.duracion; }

  /** Congela el reloj en 0 al terminar. Devuelve true solo la primera vez. */
  revisarAgotado() {
    if (this.corriendo && this._fin - this._ahora() <= 0) {
      this._fin = null;
      this._restante = 0;
      return true;
    }
    return false;
  }
}

/* ========================================================================== */
/* ESTADO COMPLETO                                                            */
/* ========================================================================== */
export class EstadoPartido {
  constructor(numEquipos = 3) {
    this.equipos = [];
    this.diseno = { ...DISENO_POR_DEFECTO };
    this.cronometro = new Cronometro(240);
    this.sonidos = Array.from({ length: NUM_SONIDOS }, (_, i) => ({
      nombre: `FX ${i + 1}`, path: '', clave: '', buffer: null,
    }));
    this.volumen = 0.8;
    this._retirados = [];
    this._deshacer = [];
    this._rehacer = [];
    this.ajustarNumeroEquipos(numEquipos);
  }

  /* --- estructura --- */
  ajustarNumeroEquipos(n) {
    n = Math.max(MIN_EQUIPOS, Math.min(Math.trunc(n), MAX_EQUIPOS));
    while (this.equipos.length < n) {
      if (this._retirados.length) { this.equipos.push(this._retirados.shift()); continue; }
      const [nombre, color] = EQUIPOS_POR_DEFECTO[this.equipos.length % EQUIPOS_POR_DEFECTO.length];
      this.equipos.push({ nombre, color, puntos: 0, faltas: 0 });
    }
    if (this.equipos.length > n) {
      // Los equipos retirados se guardan: bajar la cifra por error no debe
      // costar los nombres escritos a mano.
      this._retirados = this.equipos.slice(n).concat(this._retirados).slice(0, MAX_EQUIPOS);
      this.equipos.length = n;
    }
    return this.equipos.length;
  }

  indiceValido(i) { return Number.isInteger(i) && i >= 0 && i < this.equipos.length; }

  /* --- deshacer --- */
  _fotografiar() {
    this._deshacer.push(this.equipos.map(e => [e.puntos, e.faltas]));
    if (this._deshacer.length > PROFUNDIDAD_DESHACER) this._deshacer.shift();
    this._rehacer.length = 0;
  }

  _restaurar(foto) {
    foto.forEach(([puntos, faltas], i) => {
      if (this.equipos[i]) { this.equipos[i].puntos = puntos; this.equipos[i].faltas = faltas; }
    });
  }

  get puedeDeshacer() { return this._deshacer.length > 0; }
  get puedeRehacer() { return this._rehacer.length > 0; }

  deshacer() {
    if (!this._deshacer.length) return false;
    this._rehacer.push(this.equipos.map(e => [e.puntos, e.faltas]));
    this._restaurar(this._deshacer.pop());
    return true;
  }

  rehacer() {
    if (!this._rehacer.length) return false;
    this._deshacer.push(this.equipos.map(e => [e.puntos, e.faltas]));
    this._restaurar(this._rehacer.pop());
    return true;
  }

  /* --- marcador --- */
  sumarPuntos(i, delta) {
    if (!this.indiceValido(i)) return false;
    const nuevo = this.equipos[i].puntos + Math.trunc(delta);
    if (nuevo < 0 || nuevo > 999) return false;
    this._fotografiar();
    this.equipos[i].puntos = nuevo;
    return true;
  }

  sumarFaltas(i, delta) {
    if (!this.indiceValido(i)) return false;
    const nuevo = this.equipos[i].faltas + Math.trunc(delta);
    if (nuevo < 0 || nuevo > MAX_FALTAS) return false;
    this._fotografiar();
    this.equipos[i].faltas = nuevo;
    return true;
  }

  renombrar(i, nombre) {
    if (!this.indiceValido(i)) return false;
    this.equipos[i].nombre = String(nombre).slice(0, 40);
    return true;
  }

  pintarEquipo(i, color) {
    if (!this.indiceValido(i)) return false;
    this.equipos[i].color = String(color);
    return true;
  }

  reiniciarMarcador() {
    this._fotografiar();
    this.equipos.forEach(e => { e.puntos = 0; e.faltas = 0; });
    this.cronometro.reiniciar();
  }

  /* --- serialización (formato idéntico al de escritorio) --- */
  aDict() {
    return {
      version: 2,
      equipos: this.equipos.map(e => ({
        nombre: e.nombre, color: e.color, puntos: e.puntos, faltas: e.faltas,
      })),
      diseno: { ...this.diseno },
      sonidos: this.sonidos.map(s => ({ nombre: s.nombre, path: s.path })),
      volumen: this.volumen,
      duracion_timer: this.cronometro.duracion,
    };
  }

  aplicarDict(datos, incluirMarcador = true) {
    if (!datos || typeof datos !== 'object' || Array.isArray(datos)) {
      throw new Error('El archivo no contiene una configuración válida.');
    }

    if (Array.isArray(datos.equipos) && datos.equipos.length) {
      this._retirados.length = 0;
      this.ajustarNumeroEquipos(datos.equipos.length);
      datos.equipos.forEach((guardado, i) => {
        const eq = this.equipos[i];
        if (!eq || !guardado || typeof guardado !== 'object') return;
        eq.nombre = String(guardado.nombre ?? eq.nombre).slice(0, 40);
        eq.color = String(guardado.color ?? eq.color);
        if (incluirMarcador) {
          eq.puntos = acotarEntero(guardado.puntos, 0, 999, 0);
          eq.faltas = acotarEntero(guardado.faltas, 0, MAX_FALTAS, 0);
        }
      });
    }

    // Solo se copian las claves conocidas, respetando el tipo original.
    const d = datos.diseno;
    if (d && typeof d === 'object') {
      for (const [clave, valorPorDefecto] of Object.entries(DISENO_POR_DEFECTO)) {
        if (!(clave in d)) continue;
        const bruto = d[clave];
        if (typeof valorPorDefecto === 'boolean') this.diseno[clave] = Boolean(bruto);
        else if (typeof valorPorDefecto === 'number') {
          const num = Number(bruto);
          if (Number.isFinite(num)) {
            this.diseno[clave] = CLAVES_ENTERAS.has(clave) ? Math.trunc(num) : num;
          }
        } else if (typeof bruto === 'string') this.diseno[clave] = bruto;
      }
    }

    if (Array.isArray(datos.sonidos)) {
      datos.sonidos.forEach((guardado, i) => {
        if (this.sonidos[i] && guardado && typeof guardado === 'object') {
          this.sonidos[i].nombre = String(guardado.nombre ?? this.sonidos[i].nombre).slice(0, 24);
          this.sonidos[i].path = String(guardado.path ?? '');
        }
      });
    }

    const vol = Number(datos.volumen);
    if (Number.isFinite(vol)) this.volumen = Math.max(0, Math.min(vol, 1));

    const dur = Number(datos.duracion_timer);
    if (Number.isFinite(dur)) this.cronometro.fijar(dur);

    this._deshacer.length = 0;
    this._rehacer.length = 0;
  }

  /** Copia ligera que viaja a la ventana del tablero. */
  instantanea() {
    return {
      equipos: this.equipos.map(e => ({ ...e })),
      diseno: { ...this.diseno },
      timer: { restante: this.cronometro.restante, corriendo: this.cronometro.corriendo },
      maxFaltas: MAX_FALTAS,
    };
  }
}

function acotarEntero(valor, min, max, porDefecto) {
  const n = Number(valor);
  if (!Number.isFinite(n)) return porDefecto;
  return Math.max(min, Math.min(Math.trunc(n), max));
}
