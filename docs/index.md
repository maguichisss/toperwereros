# Documentación del proyecto

> Guía de navegación de la documentación de **Store Catalog** (sistema de
> catálogo, ventas y apartados de Toperwereros).

La documentación está dividida en cuatro audiencias:

| Área | Idioma | Audiencia | Contenido |
| --- | --- | --- | --- |
| [Técnica](technical/overview.md) | Inglés | Desarrolladores y operadores | Arquitectura, despliegue, base de datos, seguridad, pruebas |
| [Referencia de API](api-reference.md) | Inglés | Desarrolladores | Contratos HTTP completos de la API pública |
| [Negocio](business/index.md) | Español | Dueño y administración | Reglas de negocio: productos, ventas, apartados, clientes, catálogo |
| [Guías de usuario](user-guides/index.md) | Español | Usuarios del panel | Guías por rol: administrador, empleado, visor |
| [Flujos](flows/index.md) | Español | Todos | Diagramas paso a paso de los procesos principales |

## Cómo empezar a leer

1. **Si eres desarrollador** — empieza por [technical/overview.md](technical/overview.md) y sigue con
   [technical/architecture.md](technical/architecture.md).
2. **Si despliegas u operas el sistema** — [technical/deployment.md](technical/deployment.md) cubre dev,
   Raspberry Pi y Cloud Run, además de respaldos.
3. **Si defines las reglas del negocio** — [business/index.md](business/index.md).
4. **Si usas el sistema a diario** — [user-guides/index.md](user-guides/index.md).
5. **Para entender un proceso completo** — [flows/index.md](flows/index.md).

## Fuente de verdad y protección contra desvíos

- La **referencia de API** ([`api-reference.md`](api-reference.md)) es la fuente única de verdad del
  contrato público. [`backend/scripts/gen_api_docs.py`](../backend/scripts/gen_api_docs.py) la convierte en
  [`backend/docs.html`](../backend/docs.html) (la misma página servida en `/api/docs`).
- Dos pruebas de pytest verifican que la documentación no se desvíe del código:
  la matriz de permisos debe coincidir con [`app/auth.py`](../backend/app/auth.py), y [`docs.html`](../backend/docs.html)
  regenerado debe ser idéntico al archivo versionado.
- Los diagramas Mermaid se renderizan automáticamente en GitHub.