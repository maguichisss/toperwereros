# Flujo: Subir imágenes

```mermaid
flowchart TD
    A[Seleccionar archivo de imagen] --> B[Se verifica tamaño ≤ 5 MB<br/>mientras se lee en fragmentos]
    B --> C{¿Tamaño OK?}
    C -- No --> C1[400 Archivo demasiado grande (máx 5MB)]
    C -- Sí --> D[Se valida magic bytes<br/>JPEG / PNG / WebP]
    D --> E{¿Formato válido?}
    E -- No --> E1[400 Solo se permiten imágenes JPEG, PNG y WebP]
    E -- Sí --> F[Se genera nombre UUID<br/>ej. abc123….jpg]
    F --> G{¿GCS_BUCKET configurado?}
    G -- No --> H[Se guarda en uploads/<uuid>.<ext> (disco)]
    G -- Sí --> I[Se sube a Google Cloud Storage]
    H --> J["Respuesta: {&quot;image_url&quot;: &quot;/uploads/&lt;uuid&gt;.&lt;ext&gt;&quot;}"]
    I --> J
    J --> K{Dónde se usa}
    K -- "Foto de producto" --> L[POST /api/upload<br/>permiso product.edit]
    K -- "Avatar" --> M[POST /api/auth/avatar<br/>cuenta propia]
    L --> L1["Se liga con PUT /api/products/{id}<br/>(campo image_url)"]
    L1 --> L2["Al cambiar/eliminar el producto,<br/>el archivo anterior se borra"]
    M --> M1["Al volver a subir,<br/>el avatar anterior se borra"]
```

## Reglas

| Caso | Endpoint | Permiso | Límite |
| --- | --- | --- | :-: |
| Foto de producto | `POST /api/upload` | `product.edit` | 5/min/IP |
| Avatar | `POST /api/auth/avatar` | cuenta autenticada | 3/min/IP |

- Solo **JPEG, PNG, WebP** (por magic bytes, nunca por extensión).
- Máximo **5 MB**; mínimo 8 bytes.
- Nombre de archivo **aleatorio**, sanitizado (sin path del usuario).
- `safe_upload_path` evita `../` (path traversal): las URLs calculadas nunca
  escapan de `uploads/`.

Ver reglas detalladas: [Imágenes y subidas](../business/uploads.md).