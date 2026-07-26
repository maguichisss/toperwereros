# Store Catalog — Frontend

Aplicación web SPA para catálogo de productos, punto de venta (POS) y sistema de apartados. Construida con React 19 y Vite 6, sin dependencias de enrutamiento ni frameworks CSS.

## Tecnologías

| Tecnología | Versión | Uso |
|---|---|---|
| React | ^19.1.0 | UI y manejo de estado |
| Vite | ^6.3.0 | Bundler y dev server |
| html5-qrcode | ^2.3.8 | Escaneo de códigos de barras |
| CSS personalizado | — | Estilos sin framework externo |

## Requisitos previos

- Node.js 22+
- npm 10+
- Backend corriendo en `http://localhost:3001` (o la URL configurada)

## Inicio rápido

```bash
# Instalar dependencias
npm install

# Iniciar dev server (puerto 5173)
npm run dev
```

El dev server proxea automáticamente `/api` y `/uploads` al backend.

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `VITE_PROXY_TARGET` | `http://localhost:3001` | URL del backend API |
| `VITE_HTTPS_CERT` | — | Ruta al certificado HTTPS (opcional) |
| `VITE_HTTPS_KEY` | — | Ruta a la clave HTTPS (opcional) |

## Scripts disponibles

| Script | Comando | Descripción |
|---|---|---|
| `dev` | `npm run dev` | Dev server con hot reload (puerto 5173) |
| `build` | `npm run build` | Build de producción en `dist/` |
| `preview` | `npm run preview` | Preview del build de producción |

## Estructura del proyecto

```
frontend/
├── index.html                  # Entry HTML (lang="es")
├── package.json
├── vite.config.js              # Configuración de Vite (proxy, HTTPS)
├── Dockerfile                  # Node 22 Alpine, dev server
├── certs/                      # Certificados HTTPS locales
└── src/
    ├── main.jsx                # Entry point (React StrictMode)
    ├── App.jsx                 # Root: tab routing + auth gate
    ├── index.css               # Estilos globales (1600+ líneas)
    ├── utils.js                # formatPrice() helper
    ├── api/
    │   └── client.js           # Cliente API centralizado
    ├── context/
    │   └── AuthContext.jsx     # Auth, roles, permisos
    └── components/
        ├── LoginPage.jsx       # Formulario de login
        ├── ProductList.jsx     # Catálogo con búsqueda/paginación
        ├── ProductCard.jsx     # Tarjeta de producto (memoizada)
        ├── ProductForm.jsx     # Modal crear/editar producto
        ├── SaleCart.jsx        # POS carrito + historial de ventas
        ├── LayawayView.jsx     # Sistema de apartados
        ├── ProfilePage.jsx     # Perfil de usuario
        ├── ManagementPage.jsx  # Contenedor de sub-pestañas admin
        ├── CustomerManager.jsx # CRUD de clientes
        ├── ColorManager.jsx    # CRUD de colores
        ├── CategoryManager.jsx # CRUD de categorías
        ├── UserManager.jsx     # Gestión de usuarios
        ├── CameraCapture.jsx   # Captura de foto por cámara
        ├── BarcodeScanner.jsx  # Escaneo de código de barras
        ├── Lightbox.jsx        # Vista de imagen a pantalla completa
        ├── ColorSwatches.jsx   # Selector de colores con contraste
        ├── ConfirmDialog.jsx   # Modal de confirmación
        └── Toast.jsx           # Notificaciones toast
```

## Arquitectura

### SPA basado en pestañas

La aplicación no usa React Router. El estado activo se maneja con `useState` en `App.jsx`, renderizando un componente por pestaña:

| Pestaña | Componente | Visibilidad |
|---|---|---|
| Productos | `<ProductList />` | Todos los usuarios autenticados |
| Ventas | `<SaleCart />` | Todos los usuarios autenticados |
| Apartados | `<LayawayView />` | Todos los usuarios autenticados |
| Administración | `<ManagementPage />` | admin + employee |
| Perfil | `<ProfilePage />` | Todos los usuarios autenticados |

### Estado global

El estado de autenticación se gestiona vía React Context (`AuthContext`). No hay store global — cada componente maneja su estado local con `useState`/`useEffect`/`useCallback`.

### Cliente API

`api/client.js` centraliza todas las llamadas HTTP:

- Auto-adjunta `Authorization: Bearer <token>` a cada request
- Maneja respuestas 204 (retorna `null`) y 401 (limpia token y recarga)
- Parsea errores del backend (`data.detail`)

## Autenticación y permisos

### Flujo

1. `LoginPage` envía `POST /api/auth/login` con `{ username, password }`
2. Backend retorna `{ access_token }` (JWT)
3. Token se guarda en `localStorage` (`store_token`)
4. `AuthContext` llama `GET /api/auth/me` para obtener el usuario
5. `can(permission)` verifica permisos contra el mapa del rol

### Roles y permisos

| Permiso | admin | employee | viewer |
|---|:---:|:---:|:---:|
| `product.view` | ✅ | ✅ | ✅ |
| `product.create` | ✅ | ✅ | ❌ |
| `product.edit` | ✅ | ✅ | ❌ |
| `product.delete` | ✅ | ✅ | ❌ |
| `product.export` *(CSV/PDF)* | ✅ | ✅ | ❌ |
| `sale.view` | ✅ | ✅ | ✅ |
| `sale.create` | ✅ | ✅ | ❌ |
| `apartado.view` | ✅ | ✅ | ✅ |
| `apartado.create` | ✅ | ✅ | ❌ |
| `apartado.edit` | ✅ | ✅ | ❌ |
| `customer.view` | ✅ | ✅ | ✅ |
| `customer.create` | ✅ | ✅ | ❌ |
| `customer.edit` | ✅ | ✅ | ❌ |
| `customer.delete` | ✅ | ✅ | ❌ |
| `category.view` | ✅ | ✅ | ✅ |
| `category.create` | ✅ | ❌ | ❌ |
| `category.edit` | ✅ | ❌ | ❌ |
| `category.delete` | ✅ | ❌ | ❌ |
| `color.view` | ✅ | ✅ | ✅ |
| `color.create` | ✅ | ❌ | ❌ |
| `color.edit` | ✅ | ❌ | ❌ |
| `color.delete` | ✅ | ❌ | ❌ |
| `user.manage` | ✅ | ❌ | ❌ |

> **Nota:** `product.export` se implementa reutilizando `product.create` tanto en el backend (`require_permission("product.create")`) como en el frontend (`can('product.create')`). No existe como permiso separado en el backend.

### Permisos por componente

| Componente | Permiso | Acción protegida |
|---|---|---|
| `App.jsx` | `user.manage` | Pestaña "Administración" |
| `App.jsx` | `customer.create` | Pestaña "Administración" (employee) |
| `ProductList.jsx` | `product.create` | Botón "Añadir Producto", CSV, PDF |
| `ProductCard.jsx` | `product.edit` | Botones "Editar" y "Eliminar" |
| `SaleCart.jsx` | `sale.create` | Búsqueda de productos, botón "Cobrar" |
| `LayawayView.jsx` | `apartado.create` | Pestaña "Nuevo Apartado", búsqueda de productos (crear) |
| `LayawayView.jsx` | `apartado.edit` | Búsqueda de productos (detalle), formulario de abono, cancelar/completar |
| `ManagementPage.jsx` | `user.manage` | Sub-pestañas Colores, Categorías, Usuarios |

## Componentes

### Productos

- **`ProductList`** — Catálogo principal con búsqueda (debounce 300ms), paginación, exportación CSV/PDF, grilla de tarjetas.
- **`ProductCard`** — Tarjeta memoizada. Click = editar, doble click = lightbox. Muestra imagen, nombre, código, precio, stock, ubicación, colores.
- **`ProductForm`** — Modal para crear/editar productos. Soporta captura de cámara, escaneo de código de barras, rotación de imagen, selección de categorías y colores.

### Ventas (POS)

- **`SaleCart`** — Interfaz de punto de venta. Búsqueda de productos, carrito con controles de cantidad, advertencias de stock (80%), confirmación de checkout, historial de ventas con vista de detalle.

### Apartados

- **`LayawayView`** — Sistema completo de apartados. Flujo de creación (cliente + productos + depósito), vista de detalle con abonos, gestión de ítems, advertencia de vencimiento (21 días), acciones de completar/cancelar. Tres sub-componentes internos:
  - `ActiveView` — Lista de apartados activos
  - `CreateView` — Formulario de creación
  - `DetailView` — Detalle con pagos y gestión de ítems

### Administración

- **`ManagementPage`** — Contenedor con sub-pestañas. Admin ve: Clientes, Colores, Categorías, Usuarios. Employee ve: solo Clientes.
- **`CustomerManager`** — CRUD de clientes en tabla con edición inline.
- **`ColorManager`** — CRUD de colores con selector hexadecimal y vista de muestras.
- **`CategoryManager`** — CRUD simple de categorías por nombre.
- **`UserManager`** — Creación de usuarios con asignación de roles.

### Perfil

- **`ProfilePage`** — Actualización de avatar (subida directa o cámara), email, y cambio de contraseña.

### UI compartida

- **`LoginPage`** — Formulario de autenticación con manejo de errores y estado de carga.
- **`ConfirmDialog`** — Modal de confirmación con soporte ESC/Enter y auto-focus.
- **`Toast`** — Notificaciones auto-dismiss (4s) con tipos error/success/info.
- **`Lightbox`** — Vista de imagen a pantalla completa, cierra con ESC.
- **`CameraCapture`** — Captura de foto desde dispositivo (cámara trasera preferida), con fallback a input de archivo.
- **`BarcodeScanner`** — Escaneo de códigos de barras usando html5-qrcode, con feedback visual (borde verde/rojo).
- **`ColorSwatches`** — Selector de colores con texto de contraste automático.

## Sistema de estilos

CSS personalizado sin framework, usando **CSS custom properties** para theming.

### Variables principales

```css
:root {
  --primary: #1a73e8;    /* Azul principal */
  --danger: #e53935;     /* Rojo (eliminar, errores) */
  --success: #43a047;    /* Verde (éxito, stock OK) */
  --warning: #ff9800;    /* Naranja (poco stock) */
  --bg: #f5f5f5;         /* Fondo de página */
  --bg-card: #ffffff;    /* Fondo de tarjetas */
  --border: #e0e0e0;     /* Bordes generales */
}
```

### Layout

- Contenedor máximo: **1280px**, centrado
- Grid de productos: `auto-fill, minmax()` responsive
- Headers de tabla sticky en scroll horizontal

### Patrones de UI

| Patrón | Archivos CSS | Componentes |
|---|---|---|
| Cards | `.product-card`, `.layaway-card` | `ProductCard`, `LayawayView` |
| Modals | `.modal-overlay`, `.modal` | `ProductForm`, `ConfirmDialog` |
| Forms | `.form-group`, `.category-form` | Todos los managers |
| Cart | `.cart-mode`, `.cart-item`, `.cart-total-row` | `SaleCart`, `LayawayView` |
| Pagination | `.pagination`, `.btn-pagination` | `ProductList`, `SaleCart` |
| Tabs | `.sales-tabs`, `.sub-tabs` | `App`, `LayawayView`, `ManagementPage` |
| Search | `.search-input`, `.search-results` | `ProductList`, `SaleCart`, `LayawayView` |

## Despliegue

### Docker (desarrollo)

El `Dockerfile` usa Node 22 Alpine y ejecuta el dev server:

```bash
# Desde la raíz del proyecto
docker compose up -d --build
```

El frontend accesible en `http://localhost:5173`.

### Build de producción

```bash
npm run build
```

Genera archivos estáticos en `dist/`. Desplegar con cualquier servidor estático (nginx, Apache, CDN).

### Producción con Docker

Para producción, modificar el `Dockerfile` para ejecutar `npm run build` y servir con nginx:

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```
