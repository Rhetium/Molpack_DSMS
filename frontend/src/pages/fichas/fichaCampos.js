// Helpers compartidos entre FichaCrearPage y FichaEditarPage para las
// secciones con la convención <prefijo>_valor / _tolerancia / _limite /
// _unidad / _nc.

// Campos que acompañan a un prefijo medible y se descartan al marcar N/C,
// para no enviar al backend valores escritos previamente (quedarían
// persistidos junto al flag o dispararían la validación de tríos).
const SUFIJOS_VALOR = ['_valor', '_tolerancia', '_limite'];

// Alterna el flag N/C de un prefijo sobre el estado de la sección; al
// activarlo limpia los valores asociados (la unidad se conserva como
// default del formulario). Usar dentro de setDatos: setDatos((prev) =>
// toggleNc(prev, prefijo)).
export function toggleNc(prev, prefijo) {
  const ncKey = `${prefijo}_nc`;
  const activar = !prev[ncKey];
  const next = { ...prev, [ncKey]: activar };
  if (activar) {
    for (const sufijo of SUFIJOS_VALOR) {
      const campo = `${prefijo}${sufijo}`;
      if (campo in next) next[campo] = '';
    }
  }
  return next;
}

// Una sección "tiene valores" solo si el usuario ingresó algo real:
// las unidades prellenadas por defecto y los flags N/C desactivados
// no cuentan (antes hacían que la sección siempre pareciera completa).
export function tieneValores(datos) {
  return Object.entries(datos).some(([campo, v]) => {
    if (campo.endsWith('_unidad')) return false;
    if (campo.endsWith('_nc')) return v === true;
    return v !== '' && v !== null && v !== undefined && v !== false;
  });
}
