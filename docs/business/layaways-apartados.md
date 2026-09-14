# Apartados

Un apartado ("layaway") es el mecanismo de **apartar mercancía con un enganche**
y liquidarla con abonos. Mientras el apartado está activo, el producto queda
**reservado** (stock descontado) y el precio queda **congelado** al momento del
apartado.

## Ciclo de vida

```
activo (active) ──► liquidado (completed)   ←─ saldo llega a $0 (abono) o botón "Completar"
       │
       └──────► cancelado (cancelled)        ←─ cancelación manual
```

## 1. Crear un apartado

Requisitos y reglas:

| Regla | Detalle |
| --- | --- |
| Al menos un artículo | `"El apartado debe tener al menos un artículo"` |
| Cliente | `customer_id` o cliente nuevo `customer`, nunca ambos/ninguno |
| **Enganche (`deposit`) > 0** | mayor a cero obligatorio |
| **Enganche ≤ total** | el enganche no puede exceder el total del apartado |
| Stock por línea | existencias suficientes; si falta, error tipo `"Stock insuficiente…"` |
| Precio | congelado al precio actual del producto por línea |
| Total | calculado en el servidor (`Σ precio × cantidad`) |
| Saldo | `total − deposit` (primera parte a liquidar) |
| Primer abono | el enganche se **registra como primer pago** automáticamente |
| Stock | se **descuenta** por cada línea al crear |

## 2. Agregar abonos (`POST /payments`)

- Solo apartados **activos** (`"Solo se pueden agregar abonos a apartados activos"`).
- `amount > 0` y **no puede exceder el saldo pendiente** (`"El abono excede el
  saldo pendiente: $N"`).
- Cada abono reduce `balance`.
- **Liquidación automática**: cuando el saldo llega a **$0**, el apartado pasa
  a `completed` y se genera una **venta ligada** automáticamente (ver abajo).

## 3. Completar manualmente (`PATCH /complete`)

Equivalente manual de la liquidación automática:

- Solo apartados activos.
- Idempotente: si el apartado ya tiene venta ligada, **no hace nada**.
- Si aún hay saldo positivo, se **registra un abono final** por el monto
  restante y el saldo se pone en $0.
- Se crea la venta con las **mismas líneas y precios congelados** del apto. El
  stock **no se vuelve a descontar** (ya estaba reservado); solo cambia el
  "dueño": de apartado a venta.

## 4. Modificar artículos

**Agregar artículo** (activo):
- valida stock y descuenta; congela el precio actual; recalcula total y saldo.

**Quitar artículo** (activo):
- **restaura el stock** de ese artículo;
- el apartado debe **quedar con al menos un artículo** (si se quiere vaciar,
  se cancela);
- el nuevo total **no puede ser menor que los abonos ya pagados**
  (`"No se puede eliminar: el nuevo total ($N) sería menor que los abonos
  realizados ($M)"`).

**Cambiar cantidad** (activo):
- cantidad >= 1; si **sube**, descuenta la diferencia al producto con
  validación de stock; si **baja**, restaura la diferencia;
- mismo límite: nuevo total >= abonos pagados.

## 5. Editar notas (`PATCH /{id}`)

Solo apartados activos; únicamente se permite cambiar `notes`.

## 6. Cancelar (`PATCH /cancel`)

- Solo apartados activos (`"Solo se pueden cancelar apartados activos"`).
- **Regresa todo el stock** de sus artículos al catálogo.
- El estado pasa a `cancelled` y **se conserva el historial de abonos** (el
  sistema no maneja devolución de efectivo: se resuelve fuera del sistema).

## 7. Consultas

- Listado **del más reciente primero**, paginado (`page` >= 1,
  `per_page` 1–100, default 20).
- Filtros: por `status` (`active`/`completed`/`cancelled`) y por `customer_id`.
- El detalle incluye: artículos (con código y nombre del producto), **historial
  completo de abonos**, datos del cliente (nombre y teléfono), usuario que
  creó el apartado, y la venta ligada cuando aplica (`sale_id`).

## Reglas de negocio que NO existen (para no sorprenderse)

- No hay **plazo/vencimiento** automático de apartados: un apartado activo
  permanece activo hasta pagar todo o cancelarlo.
- No hay interés/moras: el total es fijo en el apartado.
- El borrado de apartado no existe: la salida es cancelarlo.
- Los **precios congelados** del apartado pueden diferir del precio actual del
  producto; la liquidación usa los congelados.