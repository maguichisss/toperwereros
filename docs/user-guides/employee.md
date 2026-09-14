# Guía del empleado

El empleado es el rol que opera el puesto: **vende, aparta y administra
productos y clientes** del día a día. No administra usuarios ni roles.

## Pestañas disponibles

- **Productos** — explorar, crear, editar y eliminar productos.
- **Apartados** — crear y dar seguimiento a los apartados.
- **Administración** → sub-pestañas **Clientes** y **Ventas**.
- **Perfil** — tu cuenta.

## Vender (POS)

En **Administración → Ventas** (o con el carrito desde Productos):

1. Busca el producto (por nombre, código, ubicación o precio) y agrégalo al
   **carrito**.
2. Ajusta cantidades si hace falta.
3. Confirma la venta.
4. El total se calcula solo (el sistema toma el precio del producto y
   descuenta el stock automáticamente).

> El stock se descuenta **solo al confirmar**; si agregas al carrito y no
> confirmas, nada se pierde ni se descuenta.

## Apartar mercancía

En **Apartados** → crear apartado:

1. Elige un **cliente** existente o crea uno nuevo (nombre, teléfono opcional).
2. Agrega los artículos a apartar.
3. Define el **enganche** (mayor a cero y menor o igual al total).
4. Confirma: el stock queda **reservado** y el precio **congelado**.

Después, en el detalle del apartado puedes:

- **Agregar abonos**: el saldo baja; al llegar a **cero**, el apartado se
  **liquida solo** y pasa al historial de ventas.
- **Agregar o quitar artículos** (con cuidado: el total no puede ser menor que
  el dinero ya abonado).
- **Cancelarlo**: regresa todo el stock a la venta.

## Administrar productos

En **Productos**:

- **Crear**: nombre (obligatorio), código (obligatorio y único), precio,
  stock, categorías, colores, ubicación y foto. Los campos no válidos se
  rechazan con mensaje claro.
- **Editar**: cambia lo que necesites; si cambias la imagen, la anterior se
  borra.
- **Eliminar**: borra el producto y su foto (pide confirmación).

## Clientes

En **Administración → Clientes**:

- **Busca primero** por nombre o teléfono antes de crear (evita duplicados).
- Crear/editar: nombre obligatorio; teléfono, email y notas opcionales.

## Errores comunes y qué significan

| Mensaje | Qué hacer |
| --- | --- |
| `Stock insuficiente para '<nombre>': N disponible(s)…` | Hay menos piezas de las pedidas; reduce la cantidad o busca otro artículo |
| `El depósito debe ser mayor a cero` | En un apartado, el enganche no puede ser $0 |
| `El abono excede el saldo pendiente: $N` | El abono no puede ser mayor que lo que falta por pagar |
| `Ya existe un producto con ese código…` | El código ya lo usa otro producto |
| `Solo se pueden agregar abonos a apartados activos` | El apartado ya se liquidó o canceló |

## Referencias de reglas

- [Ventas](../business/sales-pos.md), [Apartados](../business/layaways-apartados.md),
  [Productos](../business/products.md), [Clientes](../business/customers.md).