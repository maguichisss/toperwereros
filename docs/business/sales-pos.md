# Ventas (punto de venta)

El POS del panel permite cobrar uno o varios artículos en una sola venta.

## Cómo se registra una venta

1. Se agregan líneas: producto + cantidad (al menos **un artículo**).
2. El servidor valida **cada línea**:
   - el producto existe,
   - el stock alcanza (`stock >= cantidad`).
3. El **precio unitario se toma del producto al momento de la venta**
   (el cliente no envía precios).
4. El **total se calcula en el servidor** (`suma precio × cantidad`).
5. El stock de cada producto se **descuenta** en la misma transacción
   (punto de guardado: si cualquier línea falla, **no se descuenta nada** y no
   queda una venta parcial).
6. La venta queda asociada al **usuario autenticado** (`created_by`).

## Errores de stock (ejemplos de los mensajes)

- Sin artículos: `"La venta debe tener al menos un artículo"`.
- Falta stock: `"Stock insuficiente para '<nombre>': N disponible(s), M
  solicitado(s)"`.
- Producto inexistente: `"Producto N no encontrado"`.

## Consultas de ventas

- Listado **del más reciente primero** con paginación (`page` >= 1,
  `per_page` 1–100, default 20).
- Cada venta incluye sus **líneas** (producto, código, cantidad, precio
  unitario) y el **nombre del usuario** que la realizó.
- Filtro por **fechas** (`start_date`, `end_date`, formato `YYYY-MM-DD`):
  - inicio **inclusive** (ventas de ese día en adelante),
  - fin **inclusive** también (internamente suma 1 día), es decir el rango
    incluye ambos extremos.
- No existe "eliminar venta": el historial es permanente (la corrección es
  por proceso manual).

## Ventas que NO pasan por el POS

- Un apartado que se liquida genera venta automáticamente (ver
  [Apartados](layaways-apartados.md)): se crea la venta **sin** volver a
  descontar stock porque ya estaba reservado.