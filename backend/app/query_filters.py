"""Shared query DSL for list GET endpoints.

Supports:

- Pagination via ``skip`` / ``limit`` (with ``page`` / ``per_page`` kept as
  legacy aliases resolved in each router).
- Field operators on ``?field__op=value``:

  ====================  ======================================================
  Operator              Behaviour
  ====================  ======================================================
  ``__eq`` (default)    equal
  ``__ne``              not equal
  ``__gt`` / ``__gte``  greater than / greater or equal
  ``__lt`` / ``__lte``  less than / less or equal
  ``__like``            ILIKE, raw value (``%`` / ``_`` wildcards allowed)
  ``__contains``        case-insensitive substring (escaped)
  ``__startswith``      case-insensitive prefix (escaped)
  ``__endswith``        case-insensitive suffix (escaped)
  ``__not_like``        NOT ILIKE (raw value)
  ``__in``              value is in a comma-separated list
  ``__not_in``          value is not in a comma-separated list
  ``__is_null``         IS NULL / IS NOT NULL (``true``/``false``/``1``/``0``)
  ====================  ======================================================

- Projection via ``modo=basico|detallado`` and ``campos=a,b,c`` (comma
  separated).  When used, rows are returned as plain dicts with only the
  requested fields; otherwise routers keep their existing typed responses.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import InstrumentedAttribute, Query

from app.config import escape_like
from app.models import (
    Category,
    Color,
    Customer,
    Layaway,
    Product,
    Sale,
)

logger = logging.getLogger(__name__)

OPERATORS = {
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "like",
    "contains",
    "startswith",
    "endswith",
    "not_like",
    "in",
    "not_in",
    "is_null",
}

_TEXT_ONLY_OPS = {"like", "contains", "startswith", "endswith", "not_like"}

BOOL_TRUE = {"true", "1", "yes", "si", "on"}
BOOL_FALSE = {"false", "0", "no", "off", ""}

#: Query params that are never treated as field operators.
RESERVED = {
    "skip",
    "limit",
    "modo",
    "campos",
    "page",
    "per_page",
    "export",
    "q",
    "category_ids",
    "color_ids",
    "start_date",
    "end_date",
    "status",
    "customer_id",
}


@dataclass(frozen=True)
class FieldSpec:
    """Description of a filterable/projectable field for a model.

    Either ``column`` (a plain scalar column) or ``relation`` +
    ``target_column`` (an M2M relationship filtered through its related
    attribute, e.g. ``Product.categories.any(Category.name == ...)``).
    """

    key: str
    column: InstrumentedAttribute | None = None
    relation: InstrumentedAttribute | None = None
    target_column: InstrumentedAttribute | None = None
    selectable: bool = True

    @property
    def py_type(self) -> type:
        c = self.column if self.column is not None else self.target_column
        if c is not None:
            try:
                return c.type.python_type
            except (NotImplementedError, AttributeError):
                return str
        return str


@dataclass(frozen=True)
class ParsedFilter:
    spec: FieldSpec
    op: str
    value: Any


@dataclass(frozen=True)
class Projection:
    keys: tuple[str, ...]

    @property
    def active(self) -> bool:
        return bool(self.keys)


def _coerce_bool(raw: str, key: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in BOOL_TRUE:
        return True
    if lowered in BOOL_FALSE:
        return False
    raise HTTPException(
        400, f"Invalid value for filter {key}: '{raw}' (use true/false)"
    )


def _coerce_scalar(py_type: type, key: str, raw: str) -> Any:
    try:
        if py_type is int:
            return int(raw)
        if py_type is bool:
            return _coerce_bool(raw, key)
        if py_type is Decimal:
            return Decimal(raw)
        if py_type is datetime:
            if "T" in raw or ":" in raw:
                return datetime.fromisoformat(raw)
            return datetime.combine(date.fromisoformat(raw), time.min)
        if py_type is date:
            return date.fromisoformat(raw)
        return raw
    except (ValueError, InvalidOperation) as exc:
        raise HTTPException(400, f"Invalid value for filter {key}: '{raw}'") from exc


def _coerce_value(py_type: type, key: str, raw: str, op: str) -> Any:
    if op == "is_null":
        return _coerce_bool(raw, key)
    if op in ("in", "not_in"):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not parts:
            raise HTTPException(400, f"Filter {key} requires at least one value")
        return [_coerce_scalar(py_type, key, p) for p in parts]
    return _coerce_scalar(py_type, key, raw)


def parse_filters(
    params: dict[str, str],
    fields: dict[str, FieldSpec],
    reserved: set[str] = RESERVED,
) -> list[ParsedFilter]:
    """Parse query params into a list of operator filters.

    Args:
        params: Single-value mapping of raw query params (last duplicate wins).
        fields: Registry of filterable fields for the target model.
        reserved: Query params that are not treated as field operators.

    Returns:
        A list of ``ParsedFilter``, empty if no operator params are present.

    Raises:
        HTTPException: 400 for unknown fields, unknown operators, or values
            that fail to coerce to the field type.
    """

    parsed: list[ParsedFilter] = []
    for raw_key, raw_value in params.items():
        if raw_key in reserved:
            continue
        field, sep, op = raw_key.rpartition("__")
        if not sep or op not in OPERATORS:
            field, op = raw_key, "eq"
        spec = fields.get(field)
        if spec is None:
            raise HTTPException(400, f"Unknown filter parameter: {raw_key}")
        if op in _TEXT_ONLY_OPS and spec.py_type is not str:
            raise HTTPException(400, f"The operator '{op}' only applies to text fields")
        value = _coerce_value(spec.py_type, raw_key, raw_value, op)
        parsed.append(ParsedFilter(spec=spec, op=op, value=value))
    return parsed


def _column_condition(col, op: str, value: Any, py_type: type):
    if op == "eq":
        return col == value
    if op == "ne":
        return col != value
    if op == "gt":
        return col > value
    if op == "gte":
        return col >= value
    if op == "lt":
        return col < value
    if op == "lte":
        return col <= value
    if op == "like":
        return col.ilike(value)
    if op == "contains":
        return col.ilike(f"%{escape_like(value)}%")
    if op == "startswith":
        return col.ilike(f"{escape_like(value)}%")
    if op == "endswith":
        return col.ilike(f"%{escape_like(value)}")
    if op == "not_like":
        return ~col.ilike(value)
    if op == "in":
        return col.in_(value)
    if op == "not_in":
        return ~col.in_(value)
    if op == "is_null":
        return col.is_(None) if value else col.isnot(None)
    raise HTTPException(400, f"Unknown filter operator: {op}")


def apply_filters(query: Query, parsed: list[ParsedFilter]) -> Query:
    """Apply parsed filters to a SQLAlchemy query (filter only, no ordering)."""
    for f in parsed:
        if f.spec.relation is not None:
            condition = _column_condition(
                f.spec.target_column, f.op, f.value, f.spec.py_type
            )
            query = query.filter(f.spec.relation.any(condition))
        else:
            condition = _column_condition(
                f.spec.column, f.op, f.value, f.spec.py_type
            )
            query = query.filter(condition)
    return query


def parse_projection(
    modo: str | None,
    campos: str | None,
    fields: dict[str, FieldSpec],
    basic_fields: tuple[str, ...],
) -> Projection | None:
    """Resolve ``modo``/``campos`` to a projection, or None if unused.

    Raises:
        HTTPException: 400 for an invalid ``modo`` value or a non-selectable
            or unknown projected field.
    """

    if modo is None and campos is None:
        return None
    if modo is not None and modo not in ("basico", "detallado"):
        raise HTTPException(400, "The 'modo' parameter must be 'basico' or 'detallado'")

    if campos:
        keys = [c.strip() for c in campos.split(",") if c.strip()]
    elif modo == "basico":
        keys = list(basic_fields)
    else:
        keys = [k for k, spec in fields.items() if spec.selectable]

    for key in keys:
        spec = fields.get(key)
        if spec is None or not spec.selectable:
            raise HTTPException(400, f"Non-selectable projection field: {key}")

    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return Projection(keys=tuple(ordered))


def project_rows(rows: list[Any], projection: Projection) -> list[dict[str, Any]]:
    """Convert ORM rows into flat dicts with only the projected fields."""
    items: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for key in projection.keys:
            value = getattr(row, key)
            if isinstance(value, Decimal):
                value = float(value)
            item[key] = value
        items.append(item)
    return items


def json_response(payload: Any) -> JSONResponse:
    """Build a JSON response with proper Decimal/datetime encoding."""
    return JSONResponse(content=jsonable_encoder(payload))


def resolve_pagination(
    *,
    skip: int | None = None,
    limit: int | None = None,
    page: int = 1,
    per_page: int = 20,
    export: bool = False,
    default_paginated: bool = True,
) -> tuple[int, int | None]:
    """Resolve (offset, limit) from explicit skip/limit or legacy page/per_page.

    ``export=True`` returns everything (limit None, offset 0).  Explicit
    ``skip``/``limit`` win over pagination aliases.  When neither is present
    and ``default_paginated`` is False (endpoints that previously returned all
    rows), no limit is applied so default behaviour is unchanged.
    """

    if export:
        return 0, None
    if skip is not None or limit is not None:
        return max(skip or 0, 0), (limit if limit is not None else 100)
    if not default_paginated:
        return 0, None
    return (max(page, 1) - 1) * per_page, per_page


def _scalar_fields(model, names: list[str]) -> dict[str, FieldSpec]:
    return {name: FieldSpec(key=name, column=getattr(model, name)) for name in names}


PRODUCT_FIELDS: dict[str, FieldSpec] = _scalar_fields(
    Product,
    [
        "id",
        "code",
        "name",
        "description",
        "stock",
        "price",
        "ubicacion",
        "image_url",
        "created_at",
        "updated_at",
    ],
)
PRODUCT_FIELDS["category"] = FieldSpec(
    key="category", relation=Product.categories, target_column=Category.name, selectable=False
)
PRODUCT_FIELDS["color"] = FieldSpec(
    key="color", relation=Product.colors, target_column=Color.name, selectable=False
)
PRODUCT_BASIC: tuple[str, ...] = ("id", "code", "name", "price", "stock", "ubicacion")

CUSTOMER_FIELDS: dict[str, FieldSpec] = _scalar_fields(
    Customer, ["id", "name", "phone", "email", "notes", "created_at", "updated_at"]
)
CUSTOMER_BASIC: tuple[str, ...] = ("id", "name", "phone")

SALE_FIELDS: dict[str, FieldSpec] = _scalar_fields(
    Sale, ["id", "total", "created_by", "created_at"]
)
SALE_BASIC: tuple[str, ...] = ("id", "total", "created_at")

LAYAWAY_FIELDS: dict[str, FieldSpec] = _scalar_fields(
    Layaway,
    [
        "id",
        "customer_id",
        "total",
        "deposit",
        "balance",
        "status",
        "sale_id",
        "created_by",
        "notes",
        "created_at",
        "updated_at",
    ],
)
LAYAWAY_BASIC: tuple[str, ...] = (
    "id",
    "customer_id",
    "status",
    "total",
    "balance",
    "created_at",
)

CATEGORY_FIELDS: dict[str, FieldSpec] = _scalar_fields(
    Category, ["id", "name", "created_at", "updated_at"]
)
CATEGORY_BASIC: tuple[str, ...] = ("id", "name")

COLOR_FIELDS: dict[str, FieldSpec] = _scalar_fields(
    Color, ["id", "name", "hex", "created_at"]
)
COLOR_BASIC: tuple[str, ...] = ("id", "name", "hex")