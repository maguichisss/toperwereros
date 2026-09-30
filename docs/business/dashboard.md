# Panel (dashboard)

El **Panel** es una pestaña de la app (visible solo para admin) que resume el
estado de la tienda en un periodo: ventas, ranking de productos, reparto por
categoría, apartados, clientes e inventario. Todo se calcula en el backend con
agregados SQL; la UI solo dibuja.

- Contrato API: [api-reference.md](../api-reference.md) (sección Dashboard).
- Permiso: `dashboard.view`. No está en la matriz de roles porque lo cubre el
  comodín `*` de admin (mismo patrón que `user.manage`): **employee y viewer
  reciben 403**.

## Parámetros

| Parámetro | Default | Rango | Qué hace |
| --- | --- | --- | --- |
| `start_date` | — | `YYYY-MM-DD` | Inicio del periodo (inclusivo) |
| `end_date` | hoy | `YYYY-MM-DD` | Fin del periodo (inclusivo) |
| `dias` | `30` | 1–365 | Tamaño de la ventana cuando no hay `start_date` |
| `top` | `5` | 1–20 | Cuántos productos trae cada ranking |
| `category` | — | nombre exacto | Filtra ventas, serie diaria, ranking e inventario |

Resolución del periodo (una sola regla):

1. `end = end_date` o, si no viene, **hoy**.
2. `start = start_date` o, si no viene, `end - (dias - 1)`.
3. Si `start > end` → 400 `start_date must be before or equal to end_date`.
4. El rango **no puede pasar de 365 días** (`MAX_SPAN_DAYS`), ni siquiera con
   `start_date`/`end_date` explícitos → 400
   `The requested date range is too wide (max 365 days)`. Sin este tope, un
   rango de centuries devolvería cientos de miles de puntos en la serie diaria.
5. Si `category` no existe → 400 `Unknown category: <nombre>`.
6. El filtro SQL es semiabierto: `created_at >= start 00:00` y
   `created_at < end+1 00:00`, para incluir completo el último día.

Los parámetros aplicados vienen de vuelta en `params` de la respuesta, para que
la UI muestre qué está usando. Fechas mal formadas → 400
`Invalid date format. Use YYYY-MM-DD` (el mismo mensaje que usa
`GET /api/sales`, que también ahora devuelve 400 en vez de 500). Fechas en los
extremos (`0001-01-01`, `9999-12-31`) se acotan en vez de reventar el servidor.

## Bloques de la respuesta

| Bloque | Contenido | ¿Afecta `category`? |
| --- | --- | --- |
| `sales` | ingresos, # ventas, ticket promedio, unidades vendidas | sí |
| `daily` | ingresos y # ventas por día | sí |
| `top_products` | ranking por unidades vendidas | sí |
| `top_products_by_revenue` | ranking por ingresos | sí |
| `category_breakdown` | ingresos y unidades por categoría | **no** (es tienda completa) |
| `layaways` | apartados activos, saldo por cobrar, depósitos del periodo, apartados nuevos | **no** (tienda completa) |
| `customers` | clientes totales, nuevos del periodo, con apartado activo | **no** (tienda completa) |
| `inventory` | # SKUs, unidades, agotados, stock bajo, valor de catálogo | sí |

- Los importes son `Decimal` y salen como **string** en el JSON (ej. `"150.00"`),
  igual que el resto de la API.
- Un periodo sin ventas devuelve **ceros y listas vacías**, nunca `null`.

## Semántica del filtro por categoría

- Con `category`, los ingresos se atribuyen **por líneas** del carrito
  (`Σ cantidad × precio unitario` de los productos de esa categoría) y el
  `# ventas` cuenta ventas **distintas** que contienen esa categoría. No se usa
  `sales.total`, para no imputarle a la categoría el resto del carrito.
- Sin filtro, los ingresos son `Σ sales.total` (el importe real de la caja).
- Un producto con **varias categorías** suma su ingreso en cada una: el reparto
  por categoría no es una partición del 100 %.
- El reparto solo considera productos **con al menos una categoría** (los que no
  tienen ninguna quedan fuera del doughnut), así que su suma puede ser menor
  que los ingresos del periodo. Los porcentajes del gráfico se calculan sobre
  esa misma suma.

## Inventario y stock bajo

- `out_of_stock` cuenta productos con `stock <= 0`.
- `low_stock` cuenta productos con `0 < stock <= 3`
  (`LOW_STOCK_THRESHOLD = 3`, constante del router; hoy no es parametrizable).
- `catalog_value` es `Σ stock × price`: el valor del inventario **a precio de
  venta**, no a costo (el modelo no guarda costo de compra).

## Límites conocidos

Estos KPIs **no** se pueden calcular hoy con el esquema actual:

- **Ganancia / margen**: `Product` no tiene campo de costo.
- **Efectivo vs tarjeta**: `Sale` no guarda método de pago.
- **Apartados vencidos**: `Layaway` no tiene fecha de vencimiento.
- **Comparación contra el periodo anterior** (delta %): no implementado.
