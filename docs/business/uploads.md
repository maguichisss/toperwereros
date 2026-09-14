# Imágenes y subidas

Hay dos tipos de imagen en el sistema: **fotos de producto** y **avatares**.
Ambas pasan por las mismas validaciones de seguridad.

## Validaciones comunes (cualquier subida)

| Regla | Detalle |
| --- | --- |
| Formato | solo **JPEG, PNG, WebP**, detectado por **magic bytes** (los primeros bytes del archivo, no la extensión) |
| Tamaño máximo | **5 MB** (`MAX_SIZE`) |
| Mínimo | archivo >= 8 bytes |
| Nombre | se genera un **UUID aleatorio** (`<uuid>.jpg`), nunca el nombre del cliente |
| Almacenamiento | disco local (`UPLOAD_DIR`/`uploads/`) o **Google Cloud Storage** si `GCS_BUCKET` está configurado |
| Extensión derivada | del tipo real detectado, no de lo que diga el navegador |

Errores típicos (400):

- `"Archivo demasiado grande (máx 5MB)"`
- `"Archivo de imagen inválido"` (menos de 8 bytes)
- `"Solo se permiten imágenes JPEG, PNG y WebP"`

## Fotos de producto (`POST /api/upload`)

- Requiere permiso de **editar productos** (`product.edit`).
- Límite de 5 subidas/minuto por IP.
- Devuelve `{"image_url": "/uploads/<uuid>.<ext>"}`.
- Para usarla en un producto, se **liga manualmente** vía
  `PUT /api/products/{id}` (campo `image_url`).
- El archivo subido **no** se borra solo: se limpia cuando el producto cambia
  de imagen o se elimina (ver [Productos](products.md)).

## Avatares (`POST /api/auth/avatar`)

- Es para la cuenta del propio usuario autenticado (perfil).
- Límite de 3 subidas/minuto por IP.
- Devuelve `{"image_url": "/uploads/avatar_<hex>.<ext>"}`.
- Al volver a subir un avatar, el **anterior se borra** (local o GCS).

## Acceso a los archivos

- En modo disco local, el servidor monta `/uploads` como contenido estático, y
  los routers sirven las rutas `/uploads/...` a través del proxy (Vite en dev,
  nginx en producción).
- Un guard de seguridad (`safe_upload_path`) impide que una URL como
  `/uploads/../../etc/passwd` escape del directorio de subidas (path
  traversal).
- En modo GCS, las imágenes se sirven de Cloud Storage (URLs firmadas para el
  catálogo, con expiración configurable).

## Notas operativas

- No hay borrado manual de imágenes desde la API: se limpian por efectos
  colaterales (cambio de imagen de producto, eliminación de producto,
  re-subida de avatar). Para limpiar el disco desincronizado existe
  [`backend/db_diff_imgs.py`](../../backend/db_diff_imgs.py) como utilidad de mantenimiento.
- El respaldo de imágenes es parte del [`backup.sh`](../../backup.sh) (copia el volumen de
  uploads) — ver [deployment.md](../technical/deployment.md).