// Pasos del wizard de fichas técnicas, compartidos entre FichaCrearPage
// (accent="green") y FichaEditarPage (accent="amber"). Toman la variante
// más completa de cada paso que antes vivía duplicada en ambas páginas.
import { Check } from 'lucide-react';
import { TipCampo } from './AsistenteIA';
import { toggleNc } from './fichaCampos';

const ACCENTS = {
  green: { ring: 'focus:ring-[#29b34b]', checkbox: 'accent-[#29b34b]' },
  amber: { ring: 'focus:ring-amber-400', checkbox: 'accent-amber-500' },
};

/* ========== PASO GENÉRICO: Medidas (valor/[tolerancia]/unidad) ========== */
export function PasoMedidas({ datos, setDatos, campos, accent = 'green' }) {
  const { ring } = ACCENTS[accent];

  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  return (
    <div className="space-y-4">
      {campos.map((grupo) => {
        const isNc = !!datos[`${grupo.prefijo}_nc`];
        const inputClass = `w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 ${ring} ${
          isNc ? 'bg-gray-50 border-gray-100 text-gray-300 cursor-not-allowed' : 'border-gray-200'
        }`;
        return (
          <div key={grupo.prefijo} className={`grid gap-3 items-end ${grupo.sinTolerancia ? 'grid-cols-3' : 'grid-cols-4'}`}>
            <div className={`flex items-center justify-between ${grupo.sinTolerancia ? 'col-span-3' : 'col-span-4'}`}>
              <p className="text-sm font-medium text-gray-700">
                {grupo.label}
                <TipCampo campo={grupo.prefijo} />
              </p>
              <label className="flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isNc}
                  onChange={() => setDatos((prev) => toggleNc(prev, grupo.prefijo))}
                  className="w-3.5 h-3.5 accent-amber-500"
                />
                <span className={`text-xs font-semibold ${isNc ? 'text-amber-600' : 'text-gray-400'}`}>N/C</span>
              </label>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Valor</label>
              <input
                type="number" step="any" disabled={isNc}
                value={isNc ? '' : datos[`${grupo.prefijo}_valor`] ?? ''}
                onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
                placeholder={isNc ? 'N/C' : ''}
                className={inputClass}
              />
            </div>
            {!grupo.sinTolerancia && (
              <div>
                <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
                <input
                  type="number" step="any" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_tolerancia`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_tolerancia`, e.target.value)}
                  placeholder={isNc ? 'N/C' : ''}
                  className={inputClass}
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Unidad</label>
              <input
                type="text" disabled={isNc}
                value={isNc ? '' : datos[`${grupo.prefijo}_unidad`] ?? ''}
                onChange={(e) => handleChange(`${grupo.prefijo}_unidad`, e.target.value)}
                placeholder={isNc ? 'N/C' : ''}
                className={inputClass}
              />
            </div>
            {!grupo.sinTolerancia && <div />}
          </div>
        );
      })}
    </div>
  );
}

/* ========== PASO 2: Contenido Dinámico según tipo ========== */
export function PasoContenidoDinamico({ datos, setDatos, campos, tipoContenido, accent = 'green' }) {
  const { ring } = ACCENTS[accent];

  function handleChange(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const tc = (tipoContenido || '').toLowerCase();
  const inputBase = `px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 ${ring}`;

  return (
    <div className="space-y-6">
      {/* Especificaciones del contenido */}
      <div>
        <p className="text-sm font-semibold text-gray-700 mb-3">Especificaciones del Contenido</p>
        <p className="text-xs text-gray-500 mb-3">Características del producto que contiene el empaque (opcional).</p>
        <div className="grid grid-cols-2 gap-4">
          {(tc.includes('huevo') || tc.includes('fruta') || !tc.includes('vaso')) && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Peso del contenido {tc.includes('huevo') ? '(peso del huevo)' : tc.includes('fruta') ? '(peso de la fruta)' : ''}
              </label>
              <div className="flex gap-2">
                <input
                  type="number" step="any"
                  value={datos.peso_contenido_valor}
                  onChange={(e) => handleChange('peso_contenido_valor', e.target.value)}
                  placeholder="Ej: 60"
                  className={`flex-1 ${inputBase}`}
                />
                <select
                  value={datos.peso_contenido_unidad}
                  onChange={(e) => handleChange('peso_contenido_unidad', e.target.value)}
                  className={`w-20 px-2 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 ${ring}`}
                >
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                  <option value="oz">oz</option>
                  <option value="lb">lb</option>
                </select>
              </div>
            </div>
          )}
          {(tc.includes('vaso') || tc.includes('pote')) && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Volumen del contenido {tc.includes('vaso') ? '(volumen del vaso)' : '(volumen del pote)'}
              </label>
              <div className="flex gap-2">
                <input
                  type="number" step="any"
                  value={datos.volumen_contenido_valor}
                  onChange={(e) => handleChange('volumen_contenido_valor', e.target.value)}
                  placeholder="Ej: 12"
                  className={`flex-1 ${inputBase}`}
                />
                <select
                  value={datos.volumen_contenido_unidad}
                  onChange={(e) => handleChange('volumen_contenido_unidad', e.target.value)}
                  className={`w-20 px-2 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 ${ring}`}
                >
                  <option value="oz">oz</option>
                  <option value="ml">ml</option>
                  <option value="L">L</option>
                  <option value="gal">gal</option>
                </select>
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Calibre / Tamaño {tc.includes('huevo') ? '(AA, A, B, C)' : tc.includes('fruta') ? '(calibre de fruta)' : ''}
            </label>
            <input
              type="text"
              value={datos.calibre_contenido}
              onChange={(e) => handleChange('calibre_contenido', e.target.value)}
              placeholder={tc.includes('huevo') ? 'Ej: AA, A, B' : tc.includes('fruta') ? 'Ej: Cal. 18, Cal. 24' : 'Ej: Estándar'}
              className={`w-full ${inputBase}`}
            />
          </div>
        </div>
      </div>

      <div className="border-t border-gray-100" />

      {/* Geometría */}
      <div>
        <p className="text-sm font-semibold text-gray-700 mb-1">Geometría del Empaque</p>
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mb-3">
          Todos los campos de geometría son opcionales. Llena solo los que apliquen a este producto.
        </p>
        {campos.map((grupo) => {
          const isNc = !!datos[`${grupo.prefijo}_nc`];
          const inputClass = `w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 ${ring} ${
            isNc ? 'bg-gray-50 border-gray-100 text-gray-300 cursor-not-allowed' : 'border-gray-200'
          }`;
          return (
            <div key={grupo.prefijo} className="grid grid-cols-4 gap-3 items-end p-3 rounded-lg bg-gray-50 mb-2">
              <div className="col-span-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">
                    {grupo.label}
                    <TipCampo campo={grupo.prefijo} />
                  </span>
                  <span className="text-xs text-gray-400">Opcional</span>
                </div>
                <label className="flex items-center gap-1.5 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isNc}
                    onChange={() => setDatos((prev) => toggleNc(prev, grupo.prefijo))}
                    className="w-3.5 h-3.5 accent-amber-500"
                  />
                  <span className={`text-xs font-semibold ${isNc ? 'text-amber-600' : 'text-gray-400'}`}>N/C</span>
                </label>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Valor</label>
                <input
                  type="number" step="any" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_valor`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_valor`, e.target.value)}
                  placeholder={isNc ? 'N/C' : ''}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Tolerancia (±)</label>
                <input
                  type="number" step="any" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_tolerancia`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_tolerancia`, e.target.value)}
                  placeholder={isNc ? 'N/C' : ''}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Unidad</label>
                <input
                  type="text" disabled={isNc}
                  value={isNc ? '' : datos[`${grupo.prefijo}_unidad`] ?? ''}
                  onChange={(e) => handleChange(`${grupo.prefijo}_unidad`, e.target.value)}
                  placeholder={isNc ? 'N/C' : ''}
                  className={inputClass}
                />
              </div>
              <div />
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ========== PASO 3: Empaque y Estiba ========== */
export function PasoEmpaque({ datos, setDatos, accent = 'green' }) {
  const { ring } = ACCENTS[accent];

  function h(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const inputSm = `w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 ${ring}`;
  const inputMd = `w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 ${ring}`;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Empaque</label>
          <input type="text" value={datos.tipo_empaque} onChange={(e) => h('tipo_empaque', e.target.value)}
            placeholder="Ej: Caja corrugada" className={inputMd} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Color Empaque</label>
          <input type="text" value={datos.color_empaque} onChange={(e) => h('color_empaque', e.target.value)}
            placeholder="Ej: Kraft" className={inputMd} />
        </div>
      </div>

      <p className="text-sm font-medium text-gray-700 mt-4">Dimensiones del empaque</p>
      <div className="grid grid-cols-3 gap-3">
        {[['alto_empaque_valor', 'Alto Valor', 'number'], ['alto_empaque_tolerancia', 'Tolerancia (±)', 'number'], ['alto_empaque_unidad', 'Unidad', 'text']].map(([campo, label, tipo]) => (
          <div key={campo}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input type={tipo} step={tipo === 'number' ? 'any' : undefined} value={datos[campo]}
              onChange={(e) => h(campo, e.target.value)} className={inputSm} />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[['peso_empaque_valor', 'Peso Valor', 'number'], ['peso_empaque_tolerancia', 'Tolerancia (±)', 'number'], ['peso_empaque_unidad', 'Unidad', 'text']].map(([campo, label, tipo]) => (
          <div key={campo}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input type={tipo} step={tipo === 'number' ? 'any' : undefined} value={datos[campo]}
              onChange={(e) => h(campo, e.target.value)} className={inputSm} />
          </div>
        ))}
      </div>

      <p className="text-sm font-medium text-gray-700 mt-4">Configuración de estiba</p>
      <div className="grid grid-cols-2 gap-4">
        {[['undidades_empaque', 'Unidades por empaque'], ['empaques_estiba', 'Empaques por estiba'], ['camas_estiba', 'Camas por estiba'], ['empaques_camas_estiba', 'Empaques por cama']].map(([campo, label]) => (
          <div key={campo}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input type="number" value={datos[campo]} onChange={(e) => h(campo, e.target.value)} className={inputSm} />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ========== PASO 4: Microbiología ========== */
export function PasoMicrobiologia({ datos, setDatos, accent = 'green' }) {
  const { ring, checkbox } = ACCENTS[accent];

  function h(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const pares = [
    { prefijo: 'recuento_aerobico', label: 'Recuento aeróbico' },
    { prefijo: 'recuento_moho', label: 'Recuento de moho' },
    { prefijo: 'coliforme', label: 'Coliformes' },
    { prefijo: 'escherichia_coli', label: 'Escherichia coli' },
    { prefijo: 'salmonella_spp', label: 'Salmonella spp' },
  ];

  const metales = [
    { prefijo: 'cadmio', label: 'Cadmio' },
    { prefijo: 'plomo', label: 'Plomo' },
    { prefijo: 'mercurio', label: 'Mercurio' },
    { prefijo: 'cromo', label: 'Cromo' },
  ];

  const inputClass = (nc) =>
    `w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 ${ring} ${
      nc ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed' : 'border-gray-200'
    }`;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Parámetros Microbiológicos (valor / límite)</p>
        <div className="space-y-3">
          {pares.map((p) => {
            const nc = datos[`${p.prefijo}_nc`];
            return (
              <div key={p.prefijo} className="grid grid-cols-4 gap-3 items-end">
                <p className="text-sm text-gray-600">{p.label}</p>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Valor</label>
                  <input type="number" step="any" value={datos[`${p.prefijo}_valor`]}
                    onChange={(e) => h(`${p.prefijo}_valor`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Límite</label>
                  <input type="number" step="any" value={datos[`${p.prefijo}_limite`]}
                    onChange={(e) => h(`${p.prefijo}_limite`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div className="flex items-center gap-1.5 pb-1">
                  <input type="checkbox" id={`${p.prefijo}_nc`} checked={nc}
                    onChange={() => setDatos((prev) => toggleNc(prev, p.prefijo))}
                    className={`w-4 h-4 rounded ${checkbox}`} />
                  <label htmlFor={`${p.prefijo}_nc`} className="text-xs text-gray-500 select-none">N/C</label>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Metales Pesados (valor / unidad)</p>
        <div className="space-y-3">
          {metales.map((m) => {
            const nc = datos[`${m.prefijo}_nc`];
            return (
              <div key={m.prefijo} className="grid grid-cols-4 gap-3 items-end">
                <p className="text-sm text-gray-600">{m.label}</p>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Valor</label>
                  <input type="number" step="any" value={datos[`${m.prefijo}_valor`]}
                    onChange={(e) => h(`${m.prefijo}_valor`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Unidad</label>
                  <input type="text" value={datos[`${m.prefijo}_unidad`]}
                    onChange={(e) => h(`${m.prefijo}_unidad`, e.target.value)}
                    disabled={nc} className={inputClass(nc)} />
                </div>
                <div className="flex items-center gap-1.5 pb-1">
                  <input type="checkbox" id={`${m.prefijo}_nc`} checked={nc}
                    onChange={() => setDatos((prev) => toggleNc(prev, m.prefijo))}
                    className={`w-4 h-4 rounded ${checkbox}`} />
                  <label htmlFor={`${m.prefijo}_nc`} className="text-xs text-gray-500 select-none">N/C</label>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ========== PASO 5: Manejo y Disposición ========== */
export function PasoManejo({ datos, setDatos, accent = 'green' }) {
  const { ring } = ACCENTS[accent];

  function h(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
  }

  const campos = [
    { id: 'uso', label: 'Uso', obligatorio: true, placeholder: 'Ej: Estuche para empaque de 12 huevos frescos de gallina.' },
    { id: 'manejo', label: 'Manejo', obligatorio: true, placeholder: 'Instrucciones de manipulación del producto.' },
    { id: 'almacenamiento', label: 'Almacenamiento', obligatorio: true, placeholder: 'Condiciones de almacenamiento.' },
    { id: 'transporte', label: 'Transporte', obligatorio: true, placeholder: 'Condiciones de transporte.' },
    { id: 'vida_util', label: 'Vida Útil', obligatorio: true, placeholder: 'Ej: 24 meses desde la fecha de fabricación.' },
    { id: 'inocuidad', label: 'Inocuidad', obligatorio: false, placeholder: 'Información de inocuidad.' },
    { id: 'disposicion_pt', label: 'Disposición', obligatorio: false, placeholder: 'Disposición del producto terminado.' },
    { id: 'garantias', label: 'Garantías', obligatorio: false, placeholder: 'Información de garantía.' },
    { id: 'manipulacion', label: 'Manipulación', obligatorio: false, placeholder: 'Instrucciones adicionales de manipulación.' },
  ];

  const tieneDatos = (campo) => datos[campo] && datos[campo].toString().trim().length > 0;

  return (
    <div className="space-y-4">
      {campos.map((campo) => (
        <div key={campo.id} className={`rounded-lg transition-colors ${
          campo.obligatorio && !tieneDatos(campo.id) ? 'bg-red-50/50 p-3 border border-red-100' : ''
        }`}>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">
              {campo.label} {campo.obligatorio && <span className="text-red-500">*</span>}
              <TipCampo campo={campo.id} />
            </label>
            {tieneDatos(campo.id) && (
              <span className="text-xs text-green-600 flex items-center gap-1">
                <Check size={10} /> Completado
              </span>
            )}
          </div>
          <textarea
            value={datos[campo.id]}
            onChange={(e) => h(campo.id, e.target.value)}
            placeholder={campo.placeholder}
            rows={2}
            className={`w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 ${ring} resize-none`}
          />
        </div>
      ))}
    </div>
  );
}
