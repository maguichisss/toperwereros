# Clientes

El sistema lleva un padrón de clientes para poder asociar **apartados** y
agilizar la búsqueda al cobrar.

## Datos del cliente

| Campo | Regla |
| --- | --- |
| `name` | obligatorio |
| `phone` | opcional |
| `email` | opcional |
| `notes` | opcional (notas internas) |

- Los permisos son completos (ver/crear/editar/eliminar) para admin y employee;
  el viewer solo consulta.
- **No hay regla de unicidad de teléfono en la base de datos**: el campo es
  opcional y no es único. La buena práctica operativa es **buscar antes de
  crear** (por nombre o teléfono) y reutilizar el cliente existente para no
  duplicar registros.
- Eliminar un cliente borra su ficha; también afecta cualquier apartado que lo
  referencie (precaución) — la UI pedirá confirmación.

## Búsqueda

- Busca por **nombre o teléfono** con coincidencia parcial (ILIKE, sin
  distinguir mayúsculas), por ejemplo `q=Juan` o `q=55 12` encuentra cualquier
  cliente cuyo nombre o teléfono contenga ese texto.
- Resultados ordenados por **nombre ascendentemente**.

## Clientes creados dentro de un apartado

Al crear un apartado se puede **elegir un cliente existente** o **crear uno
nuevo en el mismo paso** (via inline). Reglas:

- Se debe indicar `customer_id` (existente) **o** el objeto `customer`
  (nuevo), nunca ambos, nunca ninguno.
- Si se envía cliente nuevo, se crea automáticamente y el apartado queda
  ligado a él.

## Vínculos

- Contrato API: [api-reference.md](../api-reference.md) (sección Customers).
- Flujo de creación de apartado con cliente: [Flujos](../flows/index.md).