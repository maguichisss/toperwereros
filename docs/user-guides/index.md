# Guías de usuario

Guías prácticas para quienes usan el sistema a diario, escritas con la
pantalla real en mente.

> El sistema tiene 4 pestañas: **Productos**, **Apartados**,
> **Administración** y **Perfil**. La pestaña Administración muestra
> sub-pestañas (Clientes, Ventas, Colores, Categorías, Usuarios) dependiendo
> del rol.

| Rol | Guía | Qué puede hacer |
| --- | --- | --- |
| [Administrador](admin.md) | Administra todo (incluye usuarios y roles) | CRUD completo + administración de usuarios |
| [Empleado](employee.md) | Opera el puesto | Productos, ventas, apartados, clientes |
| [Visor](viewer.md) | Solo consulta | Ver catálogo, ventas, apartados y clientes |

## Antes de empezar

1. Entra con tu usuario y contraseña (pestaña de inicio de sesión).
2. Solo verás lo que tu rol permite: los botones de lo no permitido **no
   aparecen**.
3. Cualquier operación que cambie stock (vender, apartar, añadir/quitar
   artículos) pide confirmación y se refleja de inmediato en el catálogo.

## Conceptos rápidos

- **Carrito**: al añadir productos en el POS/Ventas se acumulan en un
  panel; **nada se descuenta hasta confirmar la venta o el apartado**.
- **Apartado**: enganche + abonos para reservar mercancía; se liquida cuando
  el saldo llega a cero.
- **Código de producto**: es único; buscarlo es la forma más rápida de
  encontrar un artículo.

> Detalles de las reglas detrás de estos pasos: [Reglas de negocio](../business/index.md).