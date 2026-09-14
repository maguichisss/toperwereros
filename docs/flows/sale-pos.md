# Flujo: Venta (POS)

```mermaid
flowchart TD
    A[Usuario con permiso sale.create] --> B[Busca productos<br/>por nombre, código, precio, categoría o color]
    B --> C[Agrega al carrito<br/>cantidad x producto]
    C --> D{¿Hay al menos 1 artículo?}
    D -- No --> C
    D -- Sí --> E[Confirma la venta]
    E --> F[POST /api/sales]
    F --> G{Por cada línea…}
    G --> H{¿Producto existe?}
    H -- No --> H1[404 Producto N no encontrado<br/>Se cancela TODO, no se descuenta nada]
    H -- Sí --> I{¿Stock suficiente?}
    I -- No --> I1[400 Stock insuficiente<br/>Se cancela TODO]
    I -- Sí --> J[Toma precio actual, suma al total,<br/>descuenta stock (mismo savepoint)]
    G -- todas OK --> K[Crea la venta con total calculado<br/>y created_by = usuario]
    K --> L[Respuesta con venta y sus líneas]
    L --> M[Se refleja en el historial de Ventas]
```

```mermaid
sequenceDiagram
    participant U as Cajero
    participant S as SPA
    participant B as API
    participant D as BD

    U->>S: Llena carrito y confirma
    S->>B: POST /api/sales {items:[{product_id, quantity}]}
    B->>D: begin_nested (savepoint)
    loop Líneas
        B->>D: Lee producto y su stock
        B->>B: Valida existencia y stock
        B->>D: Precio = producto.price; stock -= quantity
    end
    alt Alguna validación falla
        B->>D: rollback del savepoint → stock intacto
        B-->>S: 400/404 (mensaje en español)
    else Todo válido
        B->>D: sale.total = Σ; inserta Sale + líneas
        B->>D: commit
        B-->>S: 201 id, total, items[…]
    end
```

## Invariantes

- El **total se calcula en el servidor** con el precio actual del producto.
- La venta requiere **al menos un artículo** (`"La venta debe tener al menos
  un artículo"`).
- El descuento de stock y la creación de la venta son **atómicos**: si una
  línea falla, no queda ninguna venta parcial ni stock descontado.
- **No se eliminan ventas**: el historial es permanente.
- Listado del más reciente primero, paginado, con filtro de fechas inclusivo
  en ambos extremos.

Ver reglas: [Ventas (POS)](../business/sales-pos.md).