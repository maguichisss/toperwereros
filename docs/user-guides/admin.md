# Guía del administrador

El administrador tiene acceso completo. Además de las tareas del empleado
(véase la [guía del empleado](employee.md)), administra **usuarios, roles,
colores y categorías**.

## Pestañas disponibles

- **Productos** — ver y administrar el catálogo (igual que empleado).
- **Apartados** — ver y operar apartados (igual que empleado).
- **Administración** — 5 sub-pestañas:
  - **Clientes** — padrón de clientes.
  - **Ventas** — registrar ventas / ver historial.
  - **Colores** — catálogo de colores.
  - **Categorías** — catálogo de categorías.
  - **Usuarios** — cuentas del sistema (solo admin).
- **Perfil** — tu cuenta (avatar, email, contraseña).

## Sub-pestaña Usuarios

- **Crear usuario**: nombre de usuario, contraseña, email (opcional) y **rol**
  (admin / employee / viewer). El nombre de usuario se guarda en minúsculas y
  es único.
- **Editar usuario**: puedes cambiar nombre, email, rol, contraseña y
  **activarlo/desactivarlo** (un usuario inactivo ya no puede iniciar sesión).
- **Reglas de seguridad**:
  - No puedes **desactivar tu propia cuenta**.
  - No puedes **cambiar tu propio rol**.
  - No puedes crear otro usuario con el mismo nombre de usuario o email.
- El login queda bloqueado tras 5 intentos fallidos durante 15 minutos (se
  desbloquea solo).

## Sub-pestaña Colores y Categorías

- Colores: crea con **nombre** (único) y **código hexadecimal** (`#RRGGBB`,
  por ejemplo `#FF0000`). Los colores se usan en los productos y en el
  catálogo PDF.
- Categorías: crea con **nombre** único (`Tazón`, `Botella`, `Termo`, etc.).
- Editar/eliminar aplica el cambio en los productos asociados (la rejilla del
  catálogo usa estos registros).

## Buena práctica: búsqueda antes de crear

En **Clientes**, apartados y productos: **busca antes de crear** (por nombre,
teléfono o código) para no duplicar registros. El teléfono de cliente no está
marcado como único en el sistema.

## Antes de cerrar la edición de un producto

- El **código es único**: si ya existe, el sistema lo rechaza avisando con el
  nombre del producto que lo usa.
- Cambiar la imagen borra la anterior (no se puede "recuperar"); guardar el
  archivo original es tu respaldo.

## Referencias de reglas

- [Roles y permisos](../business/roles-permissions.md) — matriz completa.
- [Productos](../business/products.md), [Clientes](../business/customers.md),
  [Catálogo PDF](../business/catalog-pdf.md).