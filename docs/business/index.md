# Reglas de negocio

Esta sección documenta **qué hace el sistema y por qué** desde el punto de
vista del negocio de Toperwereros. Está separada en dominios:

| Documento | Tema |
| --- | --- |
| [Roles y permisos](roles-permissions.md) | Quién puede hacer qué |
| [Productos](products.md) | Catálogo, búsqueda, stock, imágenes |
| [Ventas (POS)](sales-pos.md) | Cobro de ventas y descuento de stock |
| [Clientes](customers.md) | Registro y búsqueda de clientes |
| [Apartados](layaways-apartados.md) | Enganche, abonos, liquidación, cancelación |
| [Catálogo PDF](catalog-pdf.md) | Impresión del catálogo semanal |
| [Imágenes / subidas](uploads.md) | Fotos de producto y avatares |

## Principios transversales

1. **El servidor nunca confía en el cliente** para precios, totales o stock:
   todos los totales se calculan en el servidor con el precio **actual del
   producto** al momento de la venta o apartado.
2. **El stock nunca puede quedar negativo.** Toda operación que descuenta
   existencias (venta, apartado, aumentar cantidad, agregar artículo) valida
   primero el stock disponible y, si algo falla, **no descuenta nada**
   (transacciones con punto de guardado).
3. **Apartado = reservar producto.** Los apartados descuentan stock al crearse;
   si se cancelan, el stock se **regresa** al catálogo.
4. **El catálogo impreso solo muestra productos con existencia.**
5. **El sistema nunca borra el historial.** Una cancelación de apartado marca el
   estado `cancelled` pero conserva los abonos registrados; el abono al cliente
   se resuelve por fuera del sistema.

## Convenciones de estado y montos

- Montos en **pesos (MXN)**, dos decimales (`Numeric(10,2)`), prefijo `$`.
- Estados de apartado: `active` (activo) → `completed` (liquidado) o `cancelled`
  (cancelado).
- Errores de la API en **español**, pensados para mostrarse directamente en el
  panel.

> Para el contrato técnico de cada endpoint ver
> [Referencia de API](../api-reference.md). Para diagramas paso a paso ver
> [Flujos](../flows/index.md).