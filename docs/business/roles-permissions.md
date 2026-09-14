# Roles y permisos

Existen tres roles. El sistema revisa permisos **en el servidor** en cada
operación; la pantalla solo oculta lo que el usuario no puede hacer.

## Matriz de permisos

| Permiso | admin | employee | viewer |
| --- | :-: | :-: | :-: |
| **Productos** | | | |
| ver productos | ✓ | ✓ | ✓ |
| crear producto | ✓ | ✓ | – |
| editar producto | ✓ | ✓ | – |
| eliminar producto | ✓ | ✓ | – |
| **Ventas** | | | |
| ver ventas | ✓ | ✓ | ✓ |
| crear venta (cobrar) | ✓ | ✓ | – |
| **Apartados** | | | |
| ver apartados | ✓ | ✓ | ✓ |
| crear apartado | ✓ | ✓ | – |
| editar apartado (abonos, artículos, cancelar) | ✓ | ✓ | – |
| **Clientes** | | | |
| ver clientes | ✓ | ✓ | ✓ |
| crear cliente | ✓ | ✓ | – |
| editar cliente | ✓ | ✓ | – |
| eliminar cliente | ✓ | ✓ | – |
| **Catálogo / categorías / colores** | | | |
| generar catálogo PDF/HTML | ✓ | ✓ | ✓* |
| ver categorías | ✓ | ✓ | ✓ |
| ver colores | ✓ | ✓ | ✓ |
| administrar categorías | ✓ crear/editar/eliminar | solo ver | solo ver |
| administrar colores | ✓ crear/editar/eliminar | solo ver | solo ver |
| **Usuarios / roles / perfil** | | | |
| administrar usuarios | solo admin | – | – |
| administrar roles | solo admin | – | – |
| subir avatar / cambiar contraseña / editar perfil | ✓ | ✓ | ✓ |
| **Imágenes de producto** | | | |
| subir foto de producto | ✓ | ✓ (product.edit) | – |

\* Ver detalle en [Catálogo PDF](catalog-pdf.md): el endpoint pide
`product.view`, permiso que el viewer sí tiene.

## Cómo se aplican en el sistema

- **admin** tiene el comodín `*`: pasa cualquier verificación.
- **employee**: puede operar el puesto (productos, ventas, apartados,
  clientes) pero **no** administrar usuarios ni roles, y solo *ver* categorías
  y colores.
- **viewer**: modo solo lectura (explorar catálogo, consultar ventas,
  apartados y clientes, generar el PDF).

Reglas de seguridad adicionales de administración:

- No puedes **desactivarte a ti mismo**.
- No puedes **cambiar tu propio rol**.
- Crear/activar/desactivar usuarios y roles está limitado a `admin`.

## Vínculos

- Detalle técnico de la matriz: [auth-security.md](../technical/auth-security.md).
- Referencia del contrato (permisos por endpoint):
  [api-reference.md](../api-reference.md).
- Matriz verificada automáticamente contra el código por la prueba
  [`test_docs_permissions.py`](../../backend/tests/test_docs_permissions.py).