# frontend/src/ — Fuente React

## Estructura

```
src/
├── main.jsx          punto de entrada, monta <App>
├── App.jsx           rutas (React Router 7)
├── lib/
│   ├── api.js        cliente Axios con interceptores JWT
│   └── auth.jsx      Context + hook useAuth
├── layouts/
│   └── MainLayout.jsx  sidebar + outlet principal
└── pages/            una carpeta por feature (ver abajo)
```

## lib/

### `api.js`
Instancia de Axios con `baseURL = /api`. Interceptor de request agrega `Authorization: Bearer <token>` desde localStorage. Interceptor de response redirige a `/login` en 401.

### `auth.jsx`
`AuthProvider` + `useAuth()`. Expone `{ user, login, logout, isAuthenticated }`. El `user` tiene `{ usuario, nombre, rol }` decodificado del JWT.

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

- **Server state**: TanStack Query (`useQuery`, `useMutation`) para fetching y caché.
- **Form state**: React Hook Form + Zod para validación en el wizard.
- **UI state**: `useState` local por componente; no hay store global.
