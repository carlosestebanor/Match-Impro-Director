/*
 * MATCH IMPRO DIRECTOR :: ALMACÉN LOCAL (versión web)
 * ---------------------------------------------------------------------------
 * El navegador no puede recordar rutas de archivos por seguridad. Para que el
 * fondo, el logo y los efectos sigan ahí al reabrir la página, guardamos los
 * archivos completos en IndexedDB, dentro del propio navegador del operador.
 * Nada se sube a ningún servidor.
 *
 * Corporación Acción Impro · Medellín, Colombia · 2026 · CC BY 4.0
 */

const BASE = 'match-impro-director';
const ALMACEN = 'medios';
const CLAVE_CONFIG = 'match_impro_config';

let promesaBase = null;

function abrir() {
  if (promesaBase) return promesaBase;
  promesaBase = new Promise((resolver, rechazar) => {
    const solicitud = indexedDB.open(BASE, 1);
    solicitud.onupgradeneeded = () => {
      const db = solicitud.result;
      if (!db.objectStoreNames.contains(ALMACEN)) db.createObjectStore(ALMACEN);
    };
    solicitud.onsuccess = () => resolver(solicitud.result);
    solicitud.onerror = () => rechazar(solicitud.error);
  });
  return promesaBase;
}

async function transaccion(modo, accion) {
  const db = await abrir();
  return new Promise((resolver, rechazar) => {
    const tx = db.transaction(ALMACEN, modo);
    const peticion = accion(tx.objectStore(ALMACEN));
    tx.oncomplete = () => resolver(peticion ? peticion.result : undefined);
    tx.onerror = () => rechazar(tx.error);
    tx.onabort = () => rechazar(tx.error);
  });
}

/** Guarda un archivo (Blob) bajo una clave. Devuelve la clave. */
export async function guardarMedio(clave, archivo) {
  await transaccion('readwrite', almacen => almacen.put({
    blob: archivo, nombre: archivo.name || clave, tipo: archivo.type,
  }, clave));
  return clave;
}

/** Recupera { blob, nombre, tipo } o null si no existe. */
export async function leerMedio(clave) {
  if (!clave) return null;
  try {
    return (await transaccion('readonly', almacen => almacen.get(clave))) || null;
  } catch {
    return null;
  }
}

export async function borrarMedio(clave) {
  if (!clave) return;
  try { await transaccion('readwrite', almacen => almacen.delete(clave)); } catch { /* nada */ }
}

/** URL temporal para pintar una imagen o reproducir un sonido guardado. */
export async function urlDeMedio(clave) {
  const registro = await leerMedio(clave);
  return registro ? URL.createObjectURL(registro.blob) : null;
}

/* --------------------------------------------------------------------------
 * Preferencias (el mismo JSON que la versión de escritorio)
 * ------------------------------------------------------------------------ */
export function guardarConfig(datos) {
  try {
    localStorage.setItem(CLAVE_CONFIG, JSON.stringify(datos));
    return true;
  } catch {
    return false;   // Modo incógnito o almacenamiento lleno
  }
}

export function leerConfig() {
  try {
    const bruto = localStorage.getItem(CLAVE_CONFIG);
    return bruto ? JSON.parse(bruto) : null;
  } catch {
    return null;    // Preferencias corruptas: se arranca de fábrica
  }
}

export function borrarConfig() {
  try { localStorage.removeItem(CLAVE_CONFIG); } catch { /* nada */ }
}
