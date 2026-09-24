# Catálogo PDF

El sistema genera un **catálogo semanal imprimible** (PDF por defecto, CSV o
HTML) que reproduce el diseño de [`docs/card-mockup.html`](../card-mockup.html) y es apto para repartir a
clientes.

## Qué productos entran

- **Solo productos con existencia** (`stock > 0`) — los agotados nunca salen.
- Filtros opcionales:
  - `ids=1,2,3` — solo los productos indicados (comas, enteros).
  - `q=…` — texto de búsqueda sobre código, nombre, ubicación, precio,
    categoría y color (misma lógica que el buscador de productos).
  - Filtros **Query DSL** de campo: `category__eq`, `color__eq`,
    `ubicacion__contains`, `price__gte`/`price__lte`, `stock__gte`,
    `created_at__gte`/`created_at__lte`, `category__in`/`color__in` (ver
    [Query DSL](../api-reference.md)). Se combinan con `AND` junto a `ids` y
    `q`.
- `theme=…` — tema visual; cualquiera de:
  `classic`, `nocturno`, `kraft`, `elegante`, `marino`, `sol`, `cyber`,
  `vino`, `rosa`, `arcoiris`, `nebulosa`, `triangulos`, `olas`, `mandala`,
  `aurora`, `confeti`, `galaxia`, `marco`, `flores`.
- `format=pdf` (default), `html` (para vista en navegador / imprimir), o
  `csv` (datos tabulares).

## Orden de presentación

1. Los productos se ordenan por **cantidad de productos por categoría
   (desc)**, luego categoría (asc), luego color (asc), luego stock (asc);
   los que no tienen categoría van **al final**.
2. En cada página: rejilla de **4 columnas × 4 filas = 16 productos por
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

## Portada

Los catálogos PDF y HTML (no el CSV) empiezan con una **portada** previa a los
productos que muestra:

1. **Logo** de la marca — se lee de `backend/app/assets/logo.png` si el archivo
   existe; si falta, la portada se genera igual sin el logo.
2. **Nombre de la marca** — `Toperwereros` en grande.
3. **Vigencia** — `Válido de {lunes} a {domingo} | semana {N}`.
4. **Galería de productos** — 6 imágenes seleccionadas al azar entre los
   productos con foto, distribuidas en 3 filas (3 + 2 + 1). La selección es
   **determinista por semana**: la misma semana siempre muestra las mismas
   imágenes; si hay menos de 6, se muestran las disponibles.
5. **Contacto WhatsApp** — si existe la variable de entorno `WHATSAPP_NUMBER`,
   un bloque clicable con el texto `Pregunta por nuestro catálogo completo`
   sobre un botón **WhatsApp** de dos líneas (icono de la marca + "WhatsApp"
   y debajo el número a 10 dígitos, p. ej. `720 796 5588`, sin prefijo país)
   que abre `https://wa.me/<número>` con el mensaje
   `Hola, quisiera preguntar sobre algunos productos disponibles`.

`WHATSAPP_NUMBER` (por defecto `527207965588`) se envía sin el signo `+` (el
formato que espera `https://wa.me/<número>`); si se deja vacío, la portada
omite el bloque de contacto.

## Contacto por tarjeta

Cuando `WHATSAPP_NUMBER` tiene valor, cada tarjeta de producto (tanto en el
PDF como en el HTML, no en el CSV) sustituye el **código del producto** por un
enlace **"Escríbenos a"** con el icono de WhatsApp:

- el enlace abre `https://wa.me/<número>` con un mensaje prefabricado
  `Hola, sigue disponible el producto: {nombre} - {código}`;
- en el PDF el bloque es clicable (`/Annots` con acción `URI`); en el HTML es
  un `<a target="_blank">`;
- si el bloque no cabe junto al precio, se reduce el tamaño de la fuente o se
  acorta a "Escríbenos";
- sin `WHATSAPP_NUMBER` se muestra el código del producto como antes.

## Reglas de error (HTTP 400)

- `format` distinto de `pdf`/`csv`/`html` → `"El parámetro format debe ser
  'pdf', 'html' o 'csv'"`.
- `theme` desconocido → lista los válidos.
- `ids` con texto no numérico → `"El parámetro ids debe contener solo números"`.
- Filtro DSL desconocido o valor no coercible → 400 (mismo comportamiento que
  las listas).

## Consumo y archivo de descarga

- PDF: respuesta `application/pdf`, nombre predecible
  `catalogo_{lunes}_{domingo}.pdf` (adjunta).
- HTML: `text/html; charset=utf-8` (inline), ideal para imprimir desde el
  navegador.
- CSV: `text/csv; charset=utf-8` con **BOM UTF-8** (abre directo en Excel),
  archivo `catalogo.csv` (adjunta). Columnas:
  `codigo,nombre,categorias,colores,precio,stock,ubicacion,total,fecha_creacion`;
  los campos de lista se unen con `, ` y el total es `stock × precio`. El
  orden es el mismo que el PDF (recientes primero).
- Generar el catálogo requiere permiso de **ver productos** (admin, employee
  y viewer pueden).

## Notas de rendimiento

- El render carga las imágenes (disco local o GCS) y las encaja en la tarjeta
  a 72 DPI; productos con imágenes inválidas se omiten con un log (no rompen la
  generación).
- El timeout de nginx para este endpoint es de 300 s (ver
  [deployment.md](../technical/deployment.md)).