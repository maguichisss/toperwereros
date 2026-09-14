# Flujo: Apartado (enganche → abonos → liquidación)

```mermaid
flowchart TD
    A[Crear apartado] --> A1{¿Cliente?}
    A1 -- "existente (customer_id)" --> A2
    A1 -- "nuevo (customer inline)" --> A2[Se crea el cliente si es nuevo]
    A2 --> A3[Agrega artículos]
    A3 --> A4{¿Enganche > 0 y ≤ total?}
    A4 -- No --> A3
    A4 -- Sí --> A5[POST /api/layaways]
    A5 --> A6[Valida stock por línea • descuenta stock •<br/>congela precio • total = Σ<br/>balance = total − enganche<br/>enganche queda como 1er abono]
    A6 --> A7[Estado: active]

    A7 --> B[Abonos<br/>POST /payments]
    B --> B1{¿Abono > 0 y ≤ saldo?}<br/>y apartado activo
    B1 -- No --> B2[Error: abono excede el saldo]
    B1 -- Sí --> B3[balance −= abono]
    B3 --> B4{¿balance = 0?}
    B4 -- No --> A7
    B4 -- Sí --> AUTO[Liquidación automática]

    A7 --> C[Cancelar<br/>PATCH /cancel]
    C --> C1[Restaura TODO el stock]<br/>[estado = cancelled, conserva abonos]
    C --> FIN

    A7 --> D[Completar manual<br/>PATCH /complete]
    D --> AUTO

    AUTO[Se crea Sale ligada con las mismas<br/>líneas y precios congelados;<br/>saldo restante se registra como abono final<br/>si aún quedaba algo]
    AUTO --> E[Estado: completed + sale_id]
    AUTO --> D2[No se vuelve a descontar stock:<br/>ya estaba reservado]
    E --> FIN([Historial de ventas y apartados liquidados])
```

```mermaid
sequenceDiagram
    participant U as Usuario
    participant S as SPA
    participant B as API
    participant D as BD

    U->>S: Crea apartado (cliente + artículos + enganche)
    S->>B: POST /api/layaways
    B->>D: Valida cliente, enganche, stock; descuenta stock; congela precios
    B->>D: Crea apartado (active) + primer abono (deposit)
    B-->>S: 201 apartado con saldo

    loop Mientras active
        U->>S: Abono
        S->>B: POST /api/layaways/{id}/payments {amount}
        B->>B: Solo active; amount > 0 y ≤ balance
        B->>D: balance -= amount
        alt balance > 0
            B-->>S: Apartado sigue activo
        else balance == 0
            B->>D: complete_layaway: crea Sale ligada + último abono (si hacía falta) + status=completed
            B-->>S: Apartado liquidado con sale_id
        end
    end

    opt Cancelación
        U->>S: Cancela apartado
        S->>B: PATCH /api/layaways/{id}/cancel
        B->>D: Restaura stock de todas las líneas; status=cancelled
        B-->>S: Apartado cancelado (abonos conservados)
    end
```

## Invariantes

- Crear apartado **siempre descuenta stock**; cancelar **siempre lo regresa**.
- El total no baja de los abonos ya pagados: agregar/quitar artículos o
  cambiar cantidades está limitado por esa regla.
- Al quitar artículos debe quedar **al menos uno** (si se quiere vaciar, se
  cancela).
- Liquidación (auto o manual) es **idempotente**: si el apartado ya tiene
  `sale_id`, no genera otra venta.
- La venta generada usa los **precios congelados** del apartado, no el precio
  actual del producto.

Ver reglas detalladas: [Apartados](../business/layaways-apartados.md).