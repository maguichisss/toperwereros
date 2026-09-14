# Guía del visor

El rol de **visor** es de solo lectura: sirve para explorar el catálogo,
consultar ventas, apartados y clientes, y **generar el catálogo PDF** sin poder
modificar nada.

## Qué puedes hacer

| Pestaña | Acciones |
| --- | --- |
| **Productos** | Buscar, filtrar por categoría y ver el detalle de cada producto (precio, stock, foto, ubicación) |
| **Apartados** | Ver el listado, el detalle y el historial de abonos de cualquier apartado (activo, liquidado o cancelado) |
| **Administración** | Sub-pestaña **Clientes** (consulta) y **Ventas** (historial de ventas con sus líneas) |
| **Perfil** | Cambiar tu contraseña / avatar / email de tu propia cuenta |

## Generar el catálogo PDF

En **Productos**, desde la opción de catálogo puedes generar el PDF o la vista
HTML del catálogo semanal:

- Solo salen productos **con existencia**.
- Puedes filtrar por categoría, texto o selección de productos.
- Se genera como archivo `catalogo_…​.pdf` listo para imprimir o repartir.

Para el detalle del formato ver [Catálogo PDF](../business/catalog-pdf.md).

## Qué NO puedes hacer (y por qué)

- **No** crear/editar/eliminar productos, clientes ni apartados.
- **No** registrar ventas ni abonos.
- **No** administrar usuarios, roles, colores o categorías.
- El sistema simplemente **no muestra** los botones de estas acciones para tu
  rol; si intentaras llamar la API directamente, devolvería un error
  `403 No tienes permiso`.

## Sugerencia de uso

El rol visor es ideal para una **tableta o pantalla de exhibición**: consultar
existencias y precios al momento, o mostrar el catálogo a un cliente — sin
riesgo de cambios accidentales.