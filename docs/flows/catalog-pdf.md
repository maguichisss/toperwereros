# Flujo: Catálogo PDF

```mermaid
flowchart TD
    A[GET /api/catalog/pdf<br/>permiso product.view] --> B{Filtros}
    B --> B1["ids=1,2,3 (opcional)"]
    B --> B2["q=… busca en código, nombre,<br/>ubicación, precio, categoría, color"]
    B --> B3["theme (default classic)"]
    B --> B4["format: pdf (default) | html"]

    B --> C{¿Parámetros válidos?}
    C -- "format ≠ pdf/html" --> C1[400 El parámetro format…]
    C -- "theme desconocido" --> C2[400 El parámetro theme debe ser…]
    C -- "ids no numéricos" --> C3[400 El parámetro ids…]
    C -- Sí --> D[Consulta productos<br/>SOLO stock > 0<br/>+ filtros]

    D --> E[Ordenar]
    E --> E1["1) Los 64 más recientes primero<br/>(RECENT_CATALOG_COUNT)"]
    E1 --> E2["2) El resto: tamaño de categoría desc,<br/>categoría asc, color asc, stock asc<br/>(sin categoría al final)"]

    E2 --> F[Renderizar]
    F --> F1["Páginas A4: 4 columnas × 4 filas = 16 tarjetas/página"]
    F --> F2["Encabezado: «Válido de lunes a domingo | semana N» (ES)"]
    F --> F3["Tarjeta: imagen (recorte central) o inicial si no hay,<br/>nombre (máx 2 líneas), franja de precio + código"]
    F --> F4["Fondo/colores según theme (patrones incluidos)"]

    F1 --> G{¿format?}
    G -- pdf --> H[application/pdf<br/>Content-Disposition: attachment<br/>catalogo_lunes_domingo.pdf]
    G -- html --> I[text/html inline<br/>para imprimir desde el navegador]
    H --> J[Descargar e imprimir]
    I --> J
```

## Notas del flujo

- La semana se calcula de **la fecha actual**: lunes de la semana vigente →
  domingo siguiente, número de semana ISO, meses en español.
- Productos con imagen inválida se **omiten con placeholder de inicial** (no
  rompen la generación).
- Misma lógica de búsqueda que el panel de productos (con caracteres `% _ \`
  escapados).
- El cabecero y el diseño replican [`docs/card-mockup.html`](../card-mockup.html).

Ver reglas detalladas: [Catálogo PDF](../business/catalog-pdf.md).