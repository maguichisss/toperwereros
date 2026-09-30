"""Store dashboard — aggregated metrics for a period (sales, layaways, stock)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database import get_db
from app.models import (
    Category,
    Customer,
    Layaway,
    LayawayPayment,
    Product,
    Sale,
    SaleItem,
    User,
    product_categories,
)
from app.query_filters import end_of_day, parse_day
from app.schemas import (
    CategoryRank,
    CustomerKpis,
    DailyPoint,
    DashboardParams,
    DashboardSummary,
    InventoryKpis,
    LayawayKpis,
    ProductRank,
    SalesKpis,
)

router = APIRouter()

LOW_STOCK_THRESHOLD = 3
MAX_SPAN_DAYS = 365

ACTIVE_STATUS = "active"


def _dec(value: Any) -> Decimal:
    """Coerce a database aggregate into a Decimal."""
    return Decimal(str(value))


def _period(
    start_date: str | None, end_date: str | None, dias: int
) -> tuple[date, date]:
    """Resolve the requested window to concrete inclusive dates.

    The window defaults to the ``dias`` days ending today, is capped at
    ``date.min`` when the subtraction would underflow and is rejected when it
    spans more than ``MAX_SPAN_DAYS`` days.

    Args:
        start_date: Explicit inclusive start date (YYYY-MM-DD) or None.
        end_date: Explicit inclusive end date (YYYY-MM-DD) or None.
        dias: Window size in days used when ``start_date`` is missing.

    Returns:
        The inclusive ``(start, end)`` pair of dates.

    Raises:
        HTTPException: 400 if a date is malformed, the window is wider than
            ``MAX_SPAN_DAYS`` days or ``start`` is after ``end``.
    """

    end = parse_day(end_date) if end_date else date.today()
    if start_date:
        start = parse_day(start_date)
    else:
        window = timedelta(days=dias - 1)
        start = end - window if end - date.min >= window else date.min
    if (end - start).days > MAX_SPAN_DAYS:
        raise HTTPException(400, "The requested date range is too wide (max 365 days)")
    if start > end:
        raise HTTPException(400, "start_date must be before or equal to end_date")
    return start, end


def _line_items_query(query, category: str | None):
    """Anchor the FROM on ``SaleItem`` and join its sale, product and category."""
    query = query.select_from(SaleItem).join(Sale, Sale.id == SaleItem.sale_id).join(
        Product, Product.id == SaleItem.product_id
    )
    if category is not None:
        query = query.join(
            product_categories, product_categories.c.product_id == Product.id
        ).join(Category, Category.id == product_categories.c.category_id).filter(
            Category.name == category
        )
    return query


def _sales_kpis(
    db: Session, start: datetime, end: datetime, category: str | None
) -> SalesKpis:
    """Aggregate revenue, sale count, average ticket and units for the period."""
    if category is not None:
        row = (
            _line_items_query(
                db.query(
                    func.coalesce(
                        func.sum(SaleItem.quantity * SaleItem.unit_price), 0
                    ).label("revenue"),
                    func.count(func.distinct(SaleItem.sale_id)).label("sales_count"),
                    func.coalesce(func.sum(SaleItem.quantity), 0).label("units"),
                ),
                category,
            )
            .filter(Sale.created_at >= start, Sale.created_at < end)
            .one_or_none()
        )
        revenue = _dec(row.revenue) if row else Decimal("0.00")
        sales_count = int(row.sales_count) if row else 0
        units_sold = int(row.units) if row else 0
    else:
        row = (
            db.query(
                func.coalesce(func.sum(Sale.total), 0).label("revenue"),
                func.count(Sale.id).label("sales_count"),
            )
            .filter(Sale.created_at >= start, Sale.created_at < end)
            .one_or_none()
        )
        revenue = _dec(row.revenue) if row else Decimal("0.00")
        sales_count = int(row.sales_count) if row else 0
        per_sale = (
            db.query(
                SaleItem.sale_id.label("sale_id"),
                func.coalesce(func.sum(SaleItem.quantity), 0).label("units"),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(Sale.created_at >= start, Sale.created_at < end)
            .group_by(SaleItem.sale_id)
            .subquery()
        )
        units_sold = int(
            db.query(func.coalesce(func.sum(per_sale.c.units), 0)).scalar() or 0
        )
    avg_ticket = (
        revenue / Decimal(sales_count) if sales_count else Decimal("0.00")
    )
    return SalesKpis(
        revenue=revenue,
        sales_count=sales_count,
        avg_ticket=avg_ticket,
        units_sold=units_sold,
    )


def _daily_series(
    db: Session,
    start_date: date,
    end_date: date,
    start: datetime,
    end: datetime,
    category: str | None,
) -> list[DailyPoint]:
    """Build a gap-free daily sales series covering the whole window."""
    day = func.date(Sale.created_at).label("day")
    if category is not None:
        query = _line_items_query(
            db.query(
                day,
                func.coalesce(
                    func.sum(SaleItem.quantity * SaleItem.unit_price), 0
                ).label("revenue"),
                func.count(func.distinct(SaleItem.sale_id)).label("sales_count"),
            ),
            category,
        )
    else:
        query = db.query(
            day,
            func.coalesce(func.sum(Sale.total), 0).label("revenue"),
            func.count(Sale.id).label("sales_count"),
        ).select_from(Sale)
    rows = (
        query.filter(Sale.created_at >= start, Sale.created_at < end)
        .group_by(day)
        .all()
    )
    by_day = {str(row.day)[:10]: row for row in rows}
    points: list[DailyPoint] = []
    span = (end_date - start_date).days
    for offset in range(span + 1):
        key = (start_date + timedelta(days=offset)).isoformat()
        row = by_day.get(key)
        points.append(
            DailyPoint(
                date=key,
                revenue=_dec(row.revenue) if row else Decimal("0.00"),
                sales_count=int(row.sales_count) if row else 0,
            )
        )
    return points


def _product_ranks(
    db: Session,
    start: datetime,
    end: datetime,
    category: str | None,
    top: int,
    by_revenue: bool,
) -> list[ProductRank]:
    """Rank products of the period by units sold or by revenue."""
    units = func.sum(SaleItem.quantity).label("units")
    revenue = func.sum(SaleItem.quantity * SaleItem.unit_price).label("revenue")
    query = db.query(
        Product.id.label("product_id"),
        Product.code.label("code"),
        Product.name.label("name"),
        units,
        revenue,
    ).select_from(Product).join(SaleItem, SaleItem.product_id == Product.id).join(
        Sale, Sale.id == SaleItem.sale_id
    )
    if category is not None:
        query = query.join(
            product_categories, product_categories.c.product_id == Product.id
        ).join(Category, Category.id == product_categories.c.category_id).filter(
            Category.name == category
        )
    order = revenue if by_revenue else units
    rows = (
        query.filter(Sale.created_at >= start, Sale.created_at < end)
        .group_by(Product.id, Product.code, Product.name)
        .order_by(order.desc(), Product.code.asc())
        .limit(top)
        .all()
    )
    return [
        ProductRank(
            product_id=row.product_id,
            code=row.code,
            name=row.name,
            units=int(row.units),
            revenue=_dec(row.revenue),
        )
        for row in rows
    ]


def _category_breakdown(
    db: Session, start: datetime, end: datetime
) -> list[CategoryRank]:
    """Attribute period revenue and units to every category, richest first."""
    rows = (
        db.query(
            Category.name.label("category"),
            func.coalesce(
                func.sum(SaleItem.quantity * SaleItem.unit_price), 0
            ).label("revenue"),
            func.coalesce(func.sum(SaleItem.quantity), 0).label("units"),
        )
        .select_from(Category)
        .join(product_categories, product_categories.c.category_id == Category.id)
        .join(Product, Product.id == product_categories.c.product_id)
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.created_at >= start, Sale.created_at < end)
        .group_by(Category.name)
        .order_by(
            func.sum(SaleItem.quantity * SaleItem.unit_price).desc(),
            Category.name.asc(),
        )
        .all()
    )
    return [
        CategoryRank(
            category=row.category,
            revenue=_dec(row.revenue),
            units=int(row.units),
        )
        for row in rows
    ]


def _layaway_kpis(db: Session, start: datetime, end: datetime) -> LayawayKpis:
    """Aggregate active layaways, outstanding balance, deposits and new plans."""
    active = db.query(
        func.count(Layaway.id).label("active_count"),
        func.coalesce(func.sum(Layaway.balance), 0).label("outstanding_balance"),
    ).filter(Layaway.status == ACTIVE_STATUS).one_or_none()
    deposits = (
        db.query(func.coalesce(func.sum(LayawayPayment.amount), 0))
        .filter(LayawayPayment.created_at >= start, LayawayPayment.created_at < end)
        .scalar()
    )
    new_count = (
        db.query(func.count(Layaway.id))
        .filter(Layaway.created_at >= start, Layaway.created_at < end)
        .scalar()
    )
    return LayawayKpis(
        active_count=int(active.active_count) if active else 0,
        outstanding_balance=(
            _dec(active.outstanding_balance) if active else Decimal("0.00")
        ),
        deposits=_dec(deposits or 0),
        new_count=int(new_count or 0),
    )


def _customer_kpis(db: Session, start: datetime, end: datetime) -> CustomerKpis:
    """Aggregate customer totals and layaway holders."""
    total = db.query(func.count(Customer.id)).scalar()
    new_count = (
        db.query(func.count(Customer.id))
        .filter(Customer.created_at >= start, Customer.created_at < end)
        .scalar()
    )
    with_active_layaway = (
        db.query(func.count(func.distinct(Layaway.customer_id)))
        .filter(Layaway.status == ACTIVE_STATUS)
        .scalar()
    )
    return CustomerKpis(
        total=int(total or 0),
        new_count=int(new_count or 0),
        with_active_layaway=int(with_active_layaway or 0),
    )


def _inventory_kpis(
    db: Session, category: str | None
) -> InventoryKpis:
    """Aggregate catalog stock counts, alerts and value at price."""
    query = db.query(
        func.count(Product.id).label("sku_count"),
        func.coalesce(func.sum(Product.stock), 0).label("units"),
        func.count(case((Product.stock <= 0, 1))).label("out_of_stock"),
        func.count(
            case(
                (
                    and_(Product.stock > 0, Product.stock <= LOW_STOCK_THRESHOLD),
                    1,
                )
            )
        ).label("low_stock"),
        func.coalesce(
            func.sum(Product.stock * Product.price), 0
        ).label("catalog_value"),
    )
    if category is not None:
        query = query.select_from(Product).join(
            product_categories, product_categories.c.product_id == Product.id
        ).join(Category, Category.id == product_categories.c.category_id).filter(
            Category.name == category
        )
    row = query.one_or_none()
    return InventoryKpis(
        sku_count=int(row.sku_count) if row else 0,
        units=int(row.units) if row else 0,
        out_of_stock=int(row.out_of_stock) if row else 0,
        low_stock=int(row.low_stock) if row else 0,
        catalog_value=_dec(row.catalog_value) if row else Decimal("0.00"),
    )


@router.get(
    "",
    response_model=DashboardSummary,
    tags=["Dashboard"],
    summary="Store dashboard summary",
    description="Aggregated store metrics for a period: sales, daily series, top products, category split, layaways, customers and inventory. Optional start_date/end_date (YYYY-MM-DD, inclusive, at most 365 days); dias sets the default window; top sizes the product rankings; category filters the sales, series, top products and inventory blocks.",
)
def get_dashboard(
    start_date: str | None = Query(
        None, description="Start date YYYY-MM-DD (inclusive)"
    ),
    end_date: str | None = Query(
        None, description="End date YYYY-MM-DD (inclusive)"
    ),
    dias: int = Query(
        30, ge=1, le=365, description="Default window in days when no range is given"
    ),
    top: int = Query(5, ge=1, le=20, description="How many products in each ranking"),
    category: str | None = Query(
        None, min_length=1, description="Category name filter (Category.name is unique)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.view")),
) -> DashboardSummary:
    """Return the aggregated store dashboard for the resolved period.

    Every block is computed with SQL aggregates over the inclusive window
    ``[start 00:00, end 23:59:59.999999]``.  The window never spans more than
    ``MAX_SPAN_DAYS`` (365) days, so the daily series stays bounded.  When
    ``category`` is given, sales, the daily series, the product rankings and
    inventory are narrowed to that category; the category split, layaways and
    customers blocks stay global on purpose.

    Args:
        start_date: Inclusive start date (YYYY-MM-DD); defaults to ``dias`` days back.
        end_date: Inclusive end date (YYYY-MM-DD); defaults to today.
        dias: Window size in days (1–365) used when ``start_date`` is absent.
        top: Number of products per ranking (1–20).
        category: Optional category name to filter the sales/inventory blocks.
        db: Active database session.
        current_user: Authenticated user with ``dashboard.view`` permission.

    Returns:
        DashboardSummary with the resolved params and every metric block.

    Raises:
        HTTPException: 400 for a malformed date, a range wider than 365 days, an
            inverted range or an unknown category.
        HTTPException: 403 if the user lacks ``dashboard.view`` permission.
    """

    window_start, window_end = _period(start_date, end_date, dias)
    if category is not None and (
        db.query(Category).filter(Category.name == category).first() is None
    ):
        raise HTTPException(400, f"Unknown category: {category}")

    start = datetime.combine(window_start, time.min)
    end = end_of_day(window_end)

    return DashboardSummary(
        params=DashboardParams(
            dias=dias,
            top=top,
            category=category,
            start_date=window_start.isoformat(),
            end_date=window_end.isoformat(),
        ),
        sales=_sales_kpis(db, start, end, category),
        daily=_daily_series(db, window_start, window_end, start, end, category),
        top_products=_product_ranks(db, start, end, category, top, by_revenue=False),
        top_products_by_revenue=_product_ranks(
            db, start, end, category, top, by_revenue=True
        ),
        category_breakdown=_category_breakdown(db, start, end),
        layaways=_layaway_kpis(db, start, end),
        customers=_customer_kpis(db, start, end),
        inventory=_inventory_kpis(db, category),
    )
