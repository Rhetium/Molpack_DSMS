import { useState, useEffect, useRef } from 'react';
import { Upload, X, Image, FileImage, Trash2, Eye, AlertCircle } from 'lucide-react';
import api from '../../../lib/api';

const TIPOS_IMAGEN = [
  { id: 'foto_producto', label: 'Foto del Producto', descripcion: 'Fotografía real del producto terminado' },
  { id: 'plano_mecanico', label: 'Plano Mecánico', descripcion: 'Plano técnico con dimensiones y especificaciones' },
];

const MAX_SIZE_MB = 5;
const FORMATOS = '.jpg,.jpeg,.png';

export default function ImagenesFicha({ idFicha, imagenes, onActualizar, soloLectura = false }) {
  const [subiendo, setSubiendo] = useState(null);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const [imagenesRotas, setImagenesRotas] = useState({});
  const inputRefs = useRef({});

  // Resetear imágenes rotas cuando cambian los datos (upload/delete exitoso)
  useEffect(() => {
    setImagenesRotas({});
  }, [imagenes]);

  function getImagenInfo(tipo) {
    return imagenes?.[tipo] || null;
  }

  // Cache buster usando tamano_bytes del archivo actual para forzar recarga tras reemplazar
  function getImagenUrl(tipo) {
    const info = getImagenInfo(tipo);
    const v = info?.tamano_bytes ?? 0;
    return `/api/ficha/${idFicha}/imagen/${tipo}?v=${v}`;
  }

  function marcarImagenRota(tipo) {
    setImagenesRotas((prev) => ({ ...prev, [tipo]: true }));
  }

  async function handleSubir(tipo, file) {
    if (!file) return;

    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setError('Solo se aceptan imágenes JPG y PNG.');
      return;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`La imagen pesa ${(file.size / 1024 / 1024).toFixed(1)}MB. Máximo: ${MAX_SIZE_MB}MB.`);
      return;
    }

    setError(null);
    setSubiendo(tipo);

    try {
      const formData = new FormData();
      formData.append('archivo', file);
      formData.append('tipo', tipo);

      await api.post(`/ficha/${idFicha}/imagen`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (onActualizar) await onActualizar();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al subir imagen';
      setError(typeof msg === 'object' ? JSON.stringify(msg) : msg);
    } finally {
      setSubiendo(null);
    }
  }

  async function handleEliminar(tipo) {
    if (!window.confirm(`¿Eliminar la imagen ${tipo === 'foto_producto' ? 'del producto' : 'del plano mecánico'}?`)) return;

    try {
      await api.delete(`/ficha/${idFicha}/imagen/${tipo}`);
      if (onActualizar) await onActualizar();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al eliminar imagen';
      setError(typeof msg === 'object' ? JSON.stringify(msg) : msg);
    }
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <X size={16} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {TIPOS_IMAGEN.map((tipo) => {
          const info = getImagenInfo(tipo.id);
          const tieneImagen = !!info && !imagenesRotas[tipo.id];

          return (
            <div key={tipo.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileImage size={16} className="text-[#044926]" />
                  <span className="text-sm font-medium text-gray-900">{tipo.label}</span>
                </div>
                {tieneImagen && !soloLectura && (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setPreview(tipo.id)}
                      className="p-1.5 text-gray-400 hover:text-[#044926] hover:bg-green-50 rounded-lg transition-colors"
                      title="Ver imagen"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      onClick={() => handleEliminar(tipo.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Eliminar imagen"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}
                {tieneImagen && soloLectura && (
                  <button
                    onClick={() => setPreview(tipo.id)}
                    className="p-1.5 text-gray-400 hover:text-[#044926] hover:bg-green-50 rounded-lg transition-colors"
                    title="Ver imagen"
                  >
                    <Eye size={14} />
                  </button>
                )}
              </div>

              {/* Contenido */}
              <div className="p-4">
                {tieneImagen ? (
                  <div className="space-y-3">
                    {/* Thumbnail */}
                    <div
                      className="relative aspect-video bg-gray-50 rounded-lg overflow-hidden cursor-pointer group"
                      onClick={() => setPreview(tipo.id)}
                    >
                      <img
                        key={getImagenUrl(tipo.id)}
                        src={getImagenUrl(tipo.id)}
                        alt={tipo.label}
                        className="w-full h-full object-contain"
                        onError={() => marcarImagenRota(tipo.id)}
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
                        <Eye size={24} className="text-white opacity-0 group-hover:opacity-70 transition-opacity" />
                      </div>
                    </div>

                    {/* Info */}
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span className="truncate max-w-[60%]">{info.nombre_original || 'imagen'}</span>
                      <span>{info.ancho}x{info.alto}px · {(info.tamano_bytes / 1024).toFixed(0)}KB</span>
                    </div>

                    {/* Reemplazar */}
                    {!soloLectura && (
                      <button
                        onClick={() => inputRefs.current[tipo.id]?.click()}
                        disabled={subiendo === tipo.id}
                        className="w-full text-center text-xs text-[#044926] hover:text-[#29b34b] font-medium py-1.5 border border-dashed border-gray-200 rounded-lg hover:border-[#29b34b]/30 transition-colors disabled:opacity-50"
                      >
                        {subiendo === tipo.id ? 'Subiendo...' : 'Reemplazar imagen'}
                      </button>
                    )}
                  </div>
                ) : imagenesRotas[tipo.id] ? (
                  /* Imagen rota: archivo en disco no encontrado */
                  <div className="flex flex-col items-center justify-center py-6 border-2 border-dashed border-red-100 rounded-lg bg-red-50/40">
                    <AlertCircle size={22} className="text-red-400 mb-2" />
                    <p className="text-sm text-red-500 font-medium">Imagen no disponible</p>
                    {!soloLectura && (
                      <button
                        onClick={() => inputRefs.current[tipo.id]?.click()}
                        className="mt-2 text-xs text-[#044926] underline"
                      >
                        Subir nueva imagen
                      </button>
                    )}
                  </div>
                ) : soloLectura ? (
                  <div className="flex flex-col items-center justify-center py-8 border-2 border-dashed border-gray-100 rounded-lg">
                    <Image size={24} className="text-gray-300 mb-2" />
                    <p className="text-sm text-gray-400">Sin imagen</p>
                  </div>
                ) : (
                  <div
                    className="flex flex-col items-center justify-center py-8 border-2 border-dashed border-gray-200 rounded-lg cursor-pointer hover:border-[#29b34b]/50 hover:bg-[#29b34b]/5 transition-colors"
                    onClick={() => inputRefs.current[tipo.id]?.click()}
                  >
                    {subiendo === tipo.id ? (
                      <div className="w-6 h-6 border-2 border-[#29b34b]/30 border-t-[#29b34b] rounded-full animate-spin" />
                    ) : (
                      <>
                        <Upload size={24} className="text-gray-400 mb-2" />
                        <p className="text-sm font-medium text-gray-600">Subir {tipo.label.toLowerCase()}</p>
                        <p className="text-xs text-gray-400 mt-1">{tipo.descripcion}</p>
                        <p className="text-xs text-gray-400 mt-0.5">JPG o PNG · Máx {MAX_SIZE_MB}MB</p>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Input file oculto */}
              <input
                ref={(el) => { inputRefs.current[tipo.id] = el; }}
                type="file"
                accept={FORMATOS}
                className="hidden"
                onChange={(e) => {
                  handleSubir(tipo.id, e.target.files?.[0]);
                  e.target.value = '';
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Modal preview */}
      {preview && (
        <div
          className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-8"
          onClick={() => setPreview(null)}
        >
          <div className="relative max-w-4xl max-h-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setPreview(null)}
              className="absolute -top-3 -right-3 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center text-gray-500 hover:text-gray-700 z-10"
            >
              <X size={18} />
            </button>
            <img
              src={getImagenUrl(preview)}
              alt={preview}
              className="max-w-full max-h-[80vh] rounded-lg shadow-2xl"
            />
            <p className="text-center text-white/70 text-sm mt-3">
              {TIPOS_IMAGEN.find((t) => t.id === preview)?.label}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
