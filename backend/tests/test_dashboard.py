"""Tests for the store dashboard aggregate endpoint."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app.models import (
    Category,
    Customer,
    Layaway,
    LayawayPayment,
    Product,
    Sale,
    SaleItem,
)

TODAY = date.today()


def _at(day: date, hour: int = 12) -> datetime:
    """Return a datetime inside the given day."""
    return datetime.combine(day, time(hour=hour))


def _category(db, name) -> Category:
    """Create a category and return it."""
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _product(db, code, name=None, price="10.00", stock=5, categories=()) -> Product:
    """Create a product, optionally attached to categories."""
    product = Product(name=name or code, code=code, price=Decimal(price), stock=stock)
    product.categories = list(categories)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _sale(db, total, created_at, lines=()) -> Sale:
    """Create a sale with line items (``(product, quantity, unit_price)``)."""
    sale = Sale(total=Decimal(total), created_at=created_at)
    sale.items = [
        SaleItem(
            product_id=product.id,
            quantity=quantity,
            unit_price=Decimal(unit_price),
        )
        for product, quantity, unit_price in lines
    ]
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


def _layaway(db, customer, total, balance, status="active", created_at=None) -> Layaway:
    """Create a layaway for a customer."""
    layaway = Layaway(
        customer_id=customer.id,
        total=Decimal(total),
        deposit=Decimal(total) - Decimal(balance),
        balance=Decimal(balance),
        status=status,
    )
    if created_at is not None:
        layaway.created_at = created_at
    db.add(layaway)
    db.commit()
    db.refresh(layaway)
    return layaway


def _dashboard(client, headers, **params):
    """Call the dashboard endpoint and assert a 200 response."""
    resp = client.get("/api/dashboard", headers=headers, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _window(days_back=1):
    """Return explicit inclusive start/end params covering recent days."""
    return {
        "start_date": (TODAY - timedelta(days=days_back)).isoformat(),
        "end_date": TODAY.isoformat(),
    }


class TestDashboardAccess:
    def test_admin_can_view_dashboard(self, client, admin_headers):
        resp = client.get("/api/dashboard", headers=admin_headers)
        assert resp.status_code == 200

    def test_employee_cannot_view_dashboard(self, client, employee_headers):
        resp = client.get("/api/dashboard", headers=employee_headers)
        assert resp.status_code == 403

    def test_viewer_cannot_view_dashboard(self, client, viewer_headers):
        resp = client.get("/api/dashboard", headers=viewer_headers)
        assert resp.status_code == 403

    def test_unauthenticated_is_401(self, client):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 401


class TestSalesKpis:
    def test_revenue_count_avg_ticket_and_units(self, client, admin_headers, db):
        p1 = _product(db, "P1", price="10.00", stock=50)
        p2 = _product(db, "P2", price="5.00", stock=50)
        _sale(db, "100.00", _at(TODAY), [(p1, 2, "10.00")])
        _sale(db, "50.00", _at(TODAY - timedelta(days=1)), [(p2, 5, "5.00")])

        data = _dashboard(client, admin_headers, **_window())

        assert Decimal(data["sales"]["revenue"]) == Decimal("150.00")
        assert data["sales"]["sales_count"] == 2
        assert Decimal(data["sales"]["avg_ticket"]) == Decimal("75.00")
        assert data["sales"]["units_sold"] == 7

    def test_sales_outside_period_are_excluded(self, client, admin_headers, db):
        p = _product(db, "P1", stock=50)
        _sale(db, "100.00", _at(TODAY - timedelta(days=10)), [(p, 1, "10.00")])
        _sale(db, "20.00", _at(TODAY), [(p, 2, "10.00")])

        data = _dashboard(client, admin_headers, **_window())

        assert Decimal(data["sales"]["revenue"]) == Decimal("20.00")
        assert data["sales"]["sales_count"] == 1
        assert Decimal(data["sales"]["avg_ticket"]) == Decimal("20.00")
        assert data["sales"]["units_sold"] == 2


class TestDailySeries:
    def test_days_without_sales_are_filled_with_zero(self, client, admin_headers, db):
        p = _product(db, "P1", stock=50)
        _sale(db, "10.00", _at(TODAY - timedelta(days=2)), [(p, 1, "10.00")])
        _sale(db, "30.00", _at(TODAY), [(p, 3, "10.00")])

        data = _dashboard(client, admin_headers, **_window(2))

        assert len(data["daily"]) == 3
        assert [point["date"] for point in data["daily"]] == [
            (TODAY - timedelta(days=2)).isoformat(),
            (TODAY - timedelta(days=1)).isoformat(),
            TODAY.isoformat(),
        ]
        gap = data["daily"][1]
        assert Decimal(gap["revenue"]) == 0
        assert gap["sales_count"] == 0
        assert Decimal(data["daily"][0]["revenue"]) == Decimal("10.00")
        assert data["daily"][0]["sales_count"] == 1
        assert Decimal(data["daily"][2]["revenue"]) == Decimal("30.00")
        assert data["daily"][2]["sales_count"] == 1


class TestProductRankings:
    def test_rankings_respect_top_and_ordering(self, client, admin_headers, db):
        many = _product(db, "A", name="Many units", price="5.00", stock=100)
        rich = _product(db, "B", name="Big ticket", price="50.00", stock=100)
        mid = _product(db, "C", name="Middle", price="2.00", stock=100)
        _sale(db, "59.00", _at(TODAY), [(many, 3, "5.00"), (rich, 1, "50.00")])
        _sale(db, "4.00", _at(TODAY), [(mid, 2, "2.00")])

        data = _dashboard(client, admin_headers, top=2, **_window())

        by_units = data["top_products"]
        assert len(by_units) == 2
        assert [row["code"] for row in by_units] == ["A", "C"]
        assert [row["units"] for row in by_units] == [3, 2]

        by_revenue = data["top_products_by_revenue"]
        assert len(by_revenue) == 2
        assert [row["code"] for row in by_revenue] == ["B", "A"]
        assert Decimal(by_revenue[0]["revenue"]) == Decimal("50.00")
        assert by_revenue[0]["name"] == "Big ticket"

    def test_rankings_carry_product_identity(self, client, admin_headers, db):
        p = _product(db, "A1", name="Anillo", price="12.50", stock=100)
        _sale(db, "25.00", _at(TODAY), [(p, 2, "12.50")])

        data = _dashboard(client, admin_headers, **_window())

        row = data["top_products"][0]
        assert row["product_id"] == p.id
        assert row["code"] == "A1"
        assert row["name"] == "Anillo"
        assert row["units"] == 2
        assert Decimal(row["revenue"]) == Decimal("25.00")


class TestCategoryBreakdown:
    def test_revenue_split_by_category(self, client, admin_headers, db):
        ropa = _category(db, "Ropa")
        ouin = _product(db, "C1", name="Camisa", price="100.00", stock=10, categories=[ropa])
        zapato = _category(db, "Calzado")
        bota = _product(db, "Z1", name="Bota", price="250.00", stock=10, categories=[zapato])
        _sale(db, "350.00", _at(TODAY), [(ouin, 1, "100.00"), (bota, 1, "250.00")])

        data = _dashboard(client, admin_headers, **_window())

        split = {row["category"]: row for row in data["category_breakdown"]}
        assert set(split) == {"Ropa", "Calzado"}
        assert Decimal(split["Ropa"]["revenue"]) == Decimal("100.00")
        assert split["Ropa"]["units"] == 1
        assert Decimal(split["Calzado"]["revenue"]) == Decimal("250.00")
        assert split["Calzado"]["units"] == 1

    def test_multi_category_double_count_and_uncategorized_excluded(
        self, client, admin_headers, db
    ):
        """Freeze the two intentional deviations of the category split.

        The split joins ``product_categories`` with an inner join, so a product
        in two categories attributes its whole revenue to both of them (the
        split is not a 100% partition) and a product with no category is left
        out entirely. Because of that last case the split can sum to less than
        ``sales.revenue``, and the frontend percentages are computed over the
        split sum.

        Args:
            client: Authenticated TestClient.
            admin_headers: Headers for an admin user (``dashboard.view``).
            db: Session over the in-memory test database.
        """

        ropa = _category(db, "Ropa")
        zapato = _category(db, "Calzado")
        multi = _product(
            db,
            "M1",
            name="Multicategoría",
            price="10.00",
            stock=10,
            categories=[ropa, zapato],
        )
        camisa = _product(
            db, "C1", name="Camisa", price="30.00", stock=10, categories=[ropa]
        )
        suelta = _product(db, "S1", name="Sin categoría", price="50.00", stock=10)
        _sale(db, "40.00", _at(TODAY), [(multi, 1, "10.00"), (camisa, 1, "30.00")])
        _sale(db, "100.00", _at(TODAY), [(suelta, 2, "50.00")])

        data = _dashboard(client, admin_headers, **_window())

        assert Decimal(data["sales"]["revenue"]) == Decimal("140.00")
        assert data["sales"]["units_sold"] == 4

        breakdown = data["category_breakdown"]
        assert [row["category"] for row in breakdown] == ["Ropa", "Calzado"]
        split = {row["category"]: row for row in breakdown}
        assert Decimal(split["Ropa"]["revenue"]) == Decimal("40.00")
        assert split["Ropa"]["units"] == 2
        assert Decimal(split["Calzado"]["revenue"]) == Decimal("10.00")
        assert split["Calzado"]["units"] == 1

        total_split = sum(
            (Decimal(row["revenue"]) for row in breakdown), Decimal("0.00")
        )
        assert total_split == Decimal("50.00")
        assert total_split < Decimal(data["sales"]["revenue"])
        assert "Sin categoría" not in split


class TestCategoryFilter:
    def test_category_narrows_only_its_blocks(self, client, admin_headers, db):
        ropa = _category(db, "Ropa")
        camisa = _product(db, "C1", name="Camisa", price="100.00", stock=10, categories=[ropa])
        zapato = _category(db, "Calzado")
        bota = _product(db, "Z1", name="Bota", price="250.00", stock=3, categories=[zapato])
        _sale(db, "350.00", _at(TODAY), [(camisa, 1, "100.00"), (bota, 1, "250.00")])
        customer = Customer(name="Ana", created_at=_at(TODAY))
        db.add(customer)
        db.commit()
        db.refresh(customer)
        _layaway(db, customer, "500.00", "200.00")

        unfiltered = _dashboard(client, admin_headers, **_window())
        filtered = _dashboard(client, admin_headers, category="Ropa", **_window())

        assert Decimal(filtered["sales"]["revenue"]) == Decimal("100.00")
        assert filtered["sales"]["sales_count"] == 1
        assert filtered["sales"]["units_sold"] == 1
        assert Decimal(filtered["daily"][-1]["revenue"]) == Decimal("100.00")
        assert [row["code"] for row in filtered["top_products"]] == ["C1"]
        assert filtered["inventory"]["sku_count"] == 1
        assert filtered["inventory"]["units"] == 10
        assert Decimal(filtered["inventory"]["catalog_value"]) == Decimal("1000.00")
        assert filtered["layaways"] == unfiltered["layaways"]
        assert filtered["customers"] == unfiltered["customers"]
        assert filtered["category_breakdown"] == unfiltered["category_breakdown"]
        assert unfiltered["inventory"]["sku_count"] == 2

    def test_category_narrows_revenue_ranking(self, client, admin_headers, db):
        ropa = _category(db, "Ropa")
        camisa = _product(
            db, "C1", name="Camisa", price="100.00", stock=10, categories=[ropa]
        )
        bufanda = _product(
            db, "C2", name="Bufanda", price="5.00", stock=10, categories=[ropa]
        )
        zapato = _category(db, "Calzado")
        bota = _product(
            db, "Z1", name="Bota", price="250.00", stock=3, categories=[zapato]
        )
        _sale(
            db,
            "115.00",
            _at(TODAY),
            [(camisa, 1, "100.00"), (bufanda, 3, "5.00")],
        )
        _sale(db, "250.00", _at(TODAY), [(bota, 1, "250.00")])

        unfiltered = _dashboard(client, admin_headers, **_window())
        filtered = _dashboard(client, admin_headers, category="Ropa", **_window())

        unfiltered_ranking = unfiltered["top_products_by_revenue"]
        assert [row["code"] for row in unfiltered_ranking] == ["Z1", "C1", "C2"]

        filtered_ranking = filtered["top_products_by_revenue"]
        by_code = {row["code"]: row for row in filtered_ranking}
        assert set(by_code) == {"C1", "C2"}
        assert Decimal(by_code["C1"]["revenue"]) == Decimal("100.00")
        assert by_code["C2"]["units"] == 3
        assert filtered_ranking == unfiltered_ranking[1:]


class TestLayawayKpis:
    def test_active_only_balance_and_period_deposits(
        self, client, admin_headers, db
    ):
        customer = Customer(name="Ana")
        db.add(customer)
        db.commit()
        db.refresh(customer)
        active = _layaway(db, customer, "100.00", "60.00", created_at=_at(TODAY))
        _layaway(
            db, customer, "80.00", "0.00", status="completed", created_at=_at(TODAY)
        )
        db.add(
            LayawayPayment(
                layaway_id=active.id, amount=Decimal("25.00"), created_at=_at(TODAY)
            )
        )
        db.add(
            LayawayPayment(
                layaway_id=active.id,
                amount=Decimal("99.00"),
                created_at=_at(TODAY - timedelta(days=5)),
            )
        )
        db.commit()

        data = _dashboard(client, admin_headers, **_window())

        assert data["layaways"]["active_count"] == 1
        assert Decimal(data["layaways"]["outstanding_balance"]) == Decimal("60.00")
        assert Decimal(data["layaways"]["deposits"]) == Decimal("25.00")
        assert data["layaways"]["new_count"] == 2

    def test_new_layaways_only_counts_period(self, client, admin_headers, db):
        customer = Customer(name="Ana")
        db.add(customer)
        db.commit()
        db.refresh(customer)
        _layaway(db, customer, "100.00", "50.00", created_at=_at(TODAY - timedelta(days=2)))
        _layaway(db, customer, "100.00", "50.00", created_at=_at(TODAY - timedelta(days=40)))

        data = _dashboard(client, admin_headers, **_window(2))

        assert data["layaways"]["active_count"] == 2
        assert Decimal(data["layaways"]["outstanding_balance"]) == Decimal("100.00")
        assert data["layaways"]["new_count"] == 1


class TestCustomerKpis:
    def test_totals_new_and_layaway_holders(self, client, admin_headers, db):
        old = Customer(name="Viejo", created_at=_at(TODAY - timedelta(days=90)))
        fresh = Customer(name="Nuevo", created_at=_at(TODAY))
        db.add_all([old, fresh])
        db.commit()
        db.refresh(old)
        db.refresh(fresh)
        _layaway(db, old, "100.00", "40.00")
        _layaway(db, fresh, "50.00", "0.00", status="completed")

        data = _dashboard(client, admin_headers, **_window())

        assert data["customers"]["total"] == 2
        assert data["customers"]["new_count"] == 1
        assert data["customers"]["with_active_layaway"] == 1


class TestInventoryKpis:
    def test_stock_counters_and_catalog_value(self, client, admin_headers, db):
        _product(db, "S0", price="10.00", stock=0)
        _product(db, "SM2", price="10.00", stock=-2)
        _product(db, "S1", price="10.00", stock=1)
        _product(db, "S3", price="10.00", stock=3)
        _product(db, "S4", price="10.00", stock=4)
        _product(db, "S10", price="5.00", stock=10)

        data = _dashboard(client, admin_headers)

        assert data["inventory"]["sku_count"] == 6
        assert data["inventory"]["units"] == 16
        assert data["inventory"]["out_of_stock"] == 2
        assert data["inventory"]["low_stock"] == 2
        assert Decimal(data["inventory"]["catalog_value"]) == Decimal("110.00")

    def test_inventory_ignores_period(self, client, admin_headers, db):
        _product(db, "S1", price="10.00", stock=1)

        data = _dashboard(client, admin_headers, **_window(1))

        assert data["inventory"]["sku_count"] == 1
        assert data["inventory"]["low_stock"] == 1


class TestValidation:
    def test_invalid_start_date_returns_400(self, client, admin_headers):
        resp = client.get(
            "/api/dashboard", headers=admin_headers, params={"start_date": "abc"}
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid date format. Use YYYY-MM-DD"

    def test_invalid_end_date_returns_400(self, client, admin_headers):
        resp = client.get(
            "/api/dashboard", headers=admin_headers, params={"end_date": "2024-13-40"}
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid date format. Use YYYY-MM-DD"

    def test_inverted_range_returns_400(self, client, admin_headers):
        resp = client.get(
            "/api/dashboard",
            headers=admin_headers,
            params={
                "start_date": TODAY.isoformat(),
                "end_date": (TODAY - timedelta(days=3)).isoformat(),
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "start_date must be before or equal to end_date"

    def test_range_wider_than_max_span_returns_400(self, client, admin_headers):
        resp = client.get(
            "/api/dashboard",
            headers=admin_headers,
            params={"start_date": "0001-01-01", "end_date": "2100-01-01"},
        )
        only_start = client.get(
            "/api/dashboard", headers=admin_headers, params={"start_date": "0001-01-01"}
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == (
            "The requested date range is too wide (max 365 days)"
        )
        assert only_start.status_code == 400
        assert only_start.json()["detail"] == resp.json()["detail"]

    def test_span_limit_boundary(self, client, admin_headers):
        anchor = date(2024, 1, 1)
        allowed = client.get(
            "/api/dashboard",
            headers=admin_headers,
            params={
                "start_date": anchor.isoformat(),
                "end_date": (anchor + timedelta(days=365)).isoformat(),
            },
        )
        rejected = client.get(
            "/api/dashboard",
            headers=admin_headers,
            params={
                "start_date": anchor.isoformat(),
                "end_date": (anchor + timedelta(days=366)).isoformat(),
            },
        )
        assert allowed.status_code == 200
        assert len(allowed.json()["daily"]) == 366
        assert rejected.status_code == 400
        assert rejected.json()["detail"] == (
            "The requested date range is too wide (max 365 days)"
        )

    def test_unknown_category_returns_400(self, client, admin_headers):
        resp = client.get(
            "/api/dashboard", headers=admin_headers, params={"category": "NoExiste"}
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Unknown category: NoExiste"

    def test_dias_below_minimum_returns_422(self, client, admin_headers):
        resp = client.get("/api/dashboard", headers=admin_headers, params={"dias": 0})
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["loc"] == ["query", "dias"]
        assert resp.json()["detail"][0]["type"] == "greater_than_equal"

    def test_dias_above_maximum_returns_422(self, client, admin_headers):
        resp = client.get("/api/dashboard", headers=admin_headers, params={"dias": 366})
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["loc"] == ["query", "dias"]
        assert resp.json()["detail"][0]["type"] == "less_than_equal"

    def test_top_below_minimum_returns_422(self, client, admin_headers):
        resp = client.get("/api/dashboard", headers=admin_headers, params={"top": 0})
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["loc"] == ["query", "top"]
        assert resp.json()["detail"][0]["type"] == "greater_than_equal"

    def test_top_above_maximum_returns_422(self, client, admin_headers):
        resp = client.get("/api/dashboard", headers=admin_headers, params={"top": 21})
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["loc"] == ["query", "top"]
        assert resp.json()["detail"][0]["type"] == "less_than_equal"

    def test_limit_boundaries_are_accepted(self, client, admin_headers):
        smallest = _dashboard(client, admin_headers, dias=1, top=1)
        largest = _dashboard(client, admin_headers, dias=365, top=20)

        assert smallest["params"] == {
            "dias": 1,
            "top": 1,
            "category": None,
            "start_date": TODAY.isoformat(),
            "end_date": TODAY.isoformat(),
        }
        assert len(smallest["daily"]) == 1
        assert largest["params"]["dias"] == 365
        assert largest["params"]["top"] == 20
        assert len(largest["daily"]) == 365

    def test_spanish_translations(self, client, admin_headers):
        headers = {**admin_headers, "Accept-Language": "es-MX"}
        bad_date = client.get(
            "/api/dashboard", headers=headers, params={"start_date": "abc"}
        )
        bad_range = client.get(
            "/api/dashboard",
            headers=headers,
            params={
                "start_date": TODAY.isoformat(),
                "end_date": (TODAY - timedelta(days=3)).isoformat(),
            },
        )
        too_wide = client.get(
            "/api/dashboard",
            headers=headers,
            params={"start_date": "0001-01-01", "end_date": "2100-01-01"},
        )
        bad_category = client.get(
            "/api/dashboard", headers=headers, params={"category": "NoExiste"}
        )
        assert bad_date.json()["detail"] == "Formato de fecha inválido. Use YYYY-MM-DD"
        assert bad_range.json()["detail"] == (
            "start_date debe ser menor o igual que end_date"
        )
        assert too_wide.json()["detail"] == (
            "El rango de fechas solicitado es demasiado amplio (máx 365 días)"
        )
        assert bad_category.json()["detail"] == "Categoría desconocida: NoExiste"


class TestPeriodResolution:
    def test_default_window_uses_dias(self, client, admin_headers):
        data = _dashboard(client, admin_headers, dias=7)
        assert data["params"]["start_date"] == (TODAY - timedelta(days=6)).isoformat()
        assert data["params"]["end_date"] == TODAY.isoformat()
        assert len(data["daily"]) == 7

    def test_explicit_range_wins_over_dias(self, client, admin_headers):
        start = TODAY - timedelta(days=2)
        data = _dashboard(
            client, admin_headers, dias=30, start_date=start.isoformat(),
            end_date=TODAY.isoformat(),
        )
        assert data["params"]["start_date"] == start.isoformat()
        assert data["params"]["end_date"] == TODAY.isoformat()
        assert len(data["daily"]) == 3

    def test_only_start_date_ends_today(self, client, admin_headers):
        start = TODAY - timedelta(days=4)
        data = _dashboard(client, admin_headers, start_date=start.isoformat())
        assert data["params"]["start_date"] == start.isoformat()
        assert data["params"]["end_date"] == TODAY.isoformat()

    def test_params_are_echoed(self, client, admin_headers, db):
        ropa = _category(db, "Ropa")
        data = _dashboard(
            client, admin_headers, dias=14, top=3, category="Ropa", **_window(1)
        )
        assert data["params"] == {
            "dias": 14,
            "top": 3,
            "category": "Ropa",
            "start_date": (TODAY - timedelta(days=1)).isoformat(),
            "end_date": TODAY.isoformat(),
        }
        assert ropa.name == "Ropa"

    def test_max_end_date_resolves_to_a_normal_window(self, client, admin_headers):
        data = _dashboard(client, admin_headers, dias=30, end_date="9999-12-31")
        assert data["params"]["end_date"] == "9999-12-31"
        assert data["params"]["start_date"] == "9999-12-02"
        assert len(data["daily"]) == 30

    def test_min_end_date_resolves_to_a_single_day(self, client, admin_headers):
        data = _dashboard(client, admin_headers, dias=30, end_date="0001-01-01")
        assert data["params"]["start_date"] == "0001-01-01"
        assert data["params"]["end_date"] == "0001-01-01"
        assert len(data["daily"]) == 1


class TestEmptyDatabase:
    def test_empty_store_returns_zeros(self, client, admin_headers):
        data = _dashboard(client, admin_headers, dias=3)
        assert Decimal(data["sales"]["revenue"]) == 0
        assert data["sales"]["sales_count"] == 0
        assert Decimal(data["sales"]["avg_ticket"]) == 0
        assert data["sales"]["units_sold"] == 0
        assert len(data["daily"]) == 3
        assert all(Decimal(point["revenue"]) == 0 for point in data["daily"])
        assert all(point["sales_count"] == 0 for point in data["daily"])
        assert data["top_products"] == []
        assert data["top_products_by_revenue"] == []
        assert data["category_breakdown"] == []
        assert data["layaways"]["active_count"] == 0
        assert Decimal(data["layaways"]["outstanding_balance"]) == 0
        assert Decimal(data["layaways"]["deposits"]) == 0
        assert data["layaways"]["new_count"] == 0
        assert data["customers"] == {
            "total": 0,
            "new_count": 0,
            "with_active_layaway": 0,
        }
        assert data["inventory"]["sku_count"] == 0
        assert data["inventory"]["units"] == 0
        assert data["inventory"]["out_of_stock"] == 0
        assert data["inventory"]["low_stock"] == 0
        assert Decimal(data["inventory"]["catalog_value"]) == 0
