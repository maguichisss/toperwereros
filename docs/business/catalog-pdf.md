# Catálogo PDF

El sistema genera un **catálogo semanal imprimible** (PDF por defecto, o HTML)
que reproduce el diseño de [`docs/card-mockup.html`](../card-mockup.html) y es apto para repartir a
clientes.

## Qué productos entran

- **Solo productos con existencia** (`stock > 0`) — los agotados nunca salen.
- Filtros opcionales:
  - `ids=1,2,3` — solo los productos indicados (comas, enteros).
  - `q=…` — texto de búsqueda sobre código, nombre, ubicación, precio,
    categoría y color (misma lógica que el buscador de productos).
- `theme=…` — tema visual; cualquiera de:
  `classic`, `nocturno`, `kraft`, `elegante`, `marino`, `sol`, `cyber`,
  `vino`, `rosa`, `arcoiris`, `nebulosa`, `triangulos`, `olas`, `mandala`,
  `aurora`, `confeti`, `galaxia`, `marco`, `flores`.
- `format=pdf` (default) o `html` (para vista en navegador / imprimir).

## Orden de presentación

1. **Los 64 más recientes primero** (`RECENT_CATALOG_COUNT = 64`): los
   productos recién agregados encabezan el catálogo, del más nuevo al más viejo.
2. El resto sigue el orden del catálogo: por **cantidad de productos por
   categoría (desc)**, luego categoría (asc), luego color (asc), luego stock
   (asc); los que no tienen categoría van **al final**.
3. En cada página: rejilla de **4 columnas × 4 filas = 16 productos por
   página**, con encabezado semanal (ver abajo).

## Contenido de cada tarjeta

- **Imagen** del producto, recortada al centro para llenar la tarjeta; si no
  hay imagen o es inválida, se dibuja un **placeholder con la inicial** del
  nombre.
- **Nombre** (máximo 2 líneas, se trunca con puntos suspensivos implícitos si
  es largo).
- **Precio** con prefijo `$` (sin decimales por defecto) en una franja inferior,
  con el **código** del producto a la derecha.

## Encabezado semanal

Cada página lleva `"Válido de {lunes} a {domingo} | semana {N}"`, calculado
respecto a la fecha actual: el inicio es el **lunes de esta semana** y el fin el
**domingo**, en español (`enero … diciembre`), con número de semana ISO.

## Reglas de error (HTTP 400)

- `format` distinto de `pdf`/`html` → `"El parámetro format debe ser 'pdf' o
  'html'"`.
- `theme` desconocido → lista los válidos.
- `ids` con texto no numérico → `"El parámetro ids debe contener solo números"`.

## Consumo y archivo de descarga

- PDF: respuesta `application/pdf`, nombre predecible
  `catalogo_{lunes}_{domingo}.pdf` (adjunta).
- HTML: `text/html; charset=utf-8` (inline), ideal para imprimir desde el
  navegador.
- Generar el catálogo requiere permiso de **ver productos** (admin, employee
  y viewer pueden).

## Notas de rendimiento

- El render carga las imágenes (disco local o GCS) y las encaja en la tarjeta
  a 72 DPI; productos con imágenes inválidas se omiten con un log (no rompen la
  generación).
- El timeout de nginx para este endpoint es de 300 s (ver
  [deployment.md](../technical/deployment.md)).