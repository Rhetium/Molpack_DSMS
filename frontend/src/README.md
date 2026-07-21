# frontend/src/ — Fuente React

## Estructura

```
frontend/
├── lib/                 infraestructura (¡fuera de src/!)
│   ├── api.js           cliente Axios con interceptores JWT
│   └── auth.jsx         Context + hook useAuth
└── src/
    ├── main.jsx         punto de entrada, monta <App>
    ├── App.jsx          rutas (React Router 7) + QueryClientProvider
    ├── layouts/
    │   └── MainLayout.jsx  sidebar + outlet principal
    └── pages/           una carpeta por feature (ver abajo)
```

> Nota: `api.js` y `auth.jsx` viven en `frontend/lib/`, no en `src/lib/`.
> Las páginas los importan con rutas relativas (p. ej. `../../../lib/api`).

## lib/ (`frontend/lib/`)

### `api.js`
Instancia de Axios con `baseURL = /api`. Interceptor de request agrega `Authorization: Bearer <token>` desde `localStorage['dsms_token']`. Interceptor de response: ante un 401 limpia el token/usuario y redirige a `/login`.

### `auth.jsx`
`AuthProvider` + `useAuth()`. Expone `{ user, cargando, login, logout }`. Guarda `dsms_token` y `dsms_user` en `localStorage`; verifica la expiración decodificando el payload del JWT en el cliente (`atob`).

## pages/

| Carpeta | Rutas | Descripción |
|---|---|---|
| `auth/` | `/login` | Formulario de login LDAP |
| `dashboard/` | `/` | Métricas y actividad reciente del dataspace |
| `fichas/` | `/fichas` | Gestión completa de fichas técnicas |
| `materiales/` | `/materiales` | Gestión de materiales comerciales |
| `busqueda/` | `/busqueda` | Búsqueda semántica por texto libre |
| `anomalias/` | `/anomalias` | Historial y resolución de anomalías |
| `grafo/` | `/grafo` | Visualización del grafo de conocimiento |
| `auditoria/` | `/auditoria` | Log de auditoría del dataspace |

## pages/fichas/

| Componente | Descripción |
|---|---|
| `FichasPage.jsx` | Lista con filtros y acceso rápido |
| `FichaCrearPage.jsx` | Wizard de 5 pasos: Características → Contenido → Empaque → Microbiología → Manejo |
| `FichaEditarPage.jsx` | Mismo wizard cargando datos existentes |
| `FichaDetallePage.jsx` | Vista de detalle con tabs por sección, cambio de estado, exportación |
| `ImagenesFicha.jsx` | Gestión de imágenes (foto producto + plano mecánico) |
| `AsistenteIA.jsx` | Asistente IA para sugerencias en formulario |

### Campos N/C (No Calculado)

Los campos marcados N/C se persisten como `{campo_nc: true}` en el JSONB (sin el `_valor`). La función `limpiarSeccion()` en el wizard se encarga de:
- Incluir `campo_nc: true` si está marcado
- Omitir `campo_nc: false` (reducción de ruido)
- Omitir strings vacíos

En `FichaDetallePage`, `agruparCampos()` filtra automáticamente los campos NC y valores booleanos, mostrando solo los campos con datos reales.

## Gestión de estado

- **Server state / fetching**: **Axios** (`lib/api.js`) invocado con `useState` +
  `useEffect` en cada página. El filtrado de listas se hace en cliente.
- **Form state**: `useState` local + `<form onSubmit>` nativo con funciones
  propias `handleSubmit`. La validación fuerte vive en el backend (Pydantic +
  reglas de servicio).
- **Auth state**: Context API propio (`lib/auth.jsx` → `useAuth`).
- **UI state**: `useState` local por componente; no hay store global.

> ⚠️ **Dependencias declaradas pero no integradas.** `@tanstack/react-query`,
> `react-hook-form` y `zod` están en `package.json`, pero el código **no las
> usa**: de TanStack Query solo se monta el `QueryClientProvider` en `App.jsx`
> (sin `useQuery`/`useMutation`), y RHF/Zod no se importan en ninguna página.
> Quedaron previstas para una futura migración.
