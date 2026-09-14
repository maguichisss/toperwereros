# Productos

El catálogo de productos es el corazón del sistema: alimenta las ventas, los
apartados y el catálogo PDF.

## Cómo están organizados

- Cada producto tiene un **código único**, nombre, **precio**, **stock**,
  descripción, ubicación (`ubicacion`) y una foto opcional.
- Un producto puede pertenecer a **varias categorías** (`Varios`, `Tazón`,
  `Botella`, `Jarra`, `Vaso`, `Plato`, `Termo`, `Cubiertos` son las sembradas
  por defecto) y tener **varios colores**.
- El listado de productos (`/api/products`) **solo muestra productos con
  existencias** (`stock > 0`, filtro aplicado siempre).

## Reglas de creación y edición

| Regla | Detalle |
| --- | --- |
| Nombre obligatorio | se recorta al inicio/fin (no vacío) |
| Código obligatorio y único | rechaza si ya existe (avisa con el nombre del producto que lo usa) |
| Precio | número >= 0 (se acepta 0) |
| Categorías y colores | si se indican, **deben existir** (valida la cantidad encontrada) |
| Stock | entero, default `1` |
| Foto | URL almacenada; si cambia al editar, el archivo anterior se **borra** del disco/GCS (nunca quedan imágenes huérfanas) |

Al **eliminar** un producto también se borra su archivo de imagen (local o GCS).

## Búsqueda

El buscador hace una búsqueda de texto parcial (LIKE insensible a
mayúsculas, con caracteres de búsqueda escapados) sobre **todos** estos campos:

- código
- nombre
- ubicación
- precio (como texto)
- nombre de la categoría
- nombre del color

Se puede además filtrar por una o varias **categorías**
(`category_ids=1,2,3`).

## Paginación

- `page` >= 1, `per_page` de 1 a 200 (default 20), ordenado por **más reciente
  primero** (`created_at` desc).
- Modo `export=true`: devuelve **todos** los resultados sin paginar (usado para
  descargas/selección masiva).

## Notas operativas

- El stock **vende y reserva de la misma tabla**: una venta reduce stock, un
  apartado lo reduce al crearse y lo restaura al cancelarse. Por eso los
  números de existencia son siempre actuales.
- Cambiar el precio en el producto **no** afecta ventas ni apartados ya
  registrados: cada línea guarda el precio unitario al momento de la operación.