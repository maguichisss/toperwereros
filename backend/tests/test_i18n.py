"""Tests for app/i18n.py localization of API error messages.

Covers language negotiation, exact/interpolated/fallback translation, and
end-to-end behavior via the exception handlers.  The AST-based guard keeps the
canonical (English) messages in sync with the translation tables.
"""

import ast
import pathlib
import re
import sys
from types import SimpleNamespace

from app import i18n


def _req(accept_language: str = ""):
    return SimpleNamespace(headers={"accept-language": accept_language})


class TestNegotiateLang:
    def test_defaults_to_english(self):
        assert i18n.negotiate_lang(_req()) == "en"

    def test_spanish_prefix(self):
        assert i18n.negotiate_lang(_req("es-MX,es;q=0.9")) == "es"

    def test_canonical_spanish(self):
        assert i18n.negotiate_lang(_req("es")) == "es"

    def test_other_language_falls_back_to_english(self):
        assert i18n.negotiate_lang(_req("fr")) == "en"


class TestTranslate:
    def test_exact_static(self):
        assert i18n.translate("Product not found", "es") == "Producto no encontrado"

    def test_interpolated_stock(self):
        msg = "Insufficient stock for 'Botella A': 3 available, 5 requested"
        assert i18n.translate(msg, "es") == (
            "Stock insuficiente para 'Botella A': 3 disponible(s), 5 solicitado(s)"
        )

    def test_interpolated_stock_additional(self):
        msg = "Insufficient stock for 'Botella A': 2 available, 1 additional requested"
        assert i18n.translate(msg, "es") == (
            "Stock insuficiente para 'Botella A': 2 disponible(s), 1 adicional(es) solicitado(s)"
        )

    def test_interpolated_payment(self):
        assert i18n.translate("Payment exceeds the pending balance: $125.50", "es") == (
            "El abono excede el saldo pendiente: $125.50"
        )

    def test_interpolated_cannot_remove(self):
        msg = "Cannot remove: the new total ($100.00) would be less than the payments made ($125.50)"
        assert i18n.translate(msg, "es") == (
            "No se puede eliminar: el nuevo total ($100.00) sería menor que los abonos realizados ($125.50)"
        )

    def test_interpolated_cannot_reduce(self):
        msg = "Cannot reduce: the new total ($100.00) would be less than the payments made ($125.50)"
        assert i18n.translate(msg, "es") == (
            "No se puede reducir: el nuevo total ($100.00) sería menor que los abonos realizados ($125.50)"
        )

    def test_interpolated_duplicate_code(self):
        assert i18n.translate("A product with code 'ABC' already exists", "es") == (
            "Ya existe un producto con ese código: 'ABC'"
        )

    def test_unknown_falls_back_to_english(self):
        assert i18n.translate("Something completely new", "es") == "Something completely new"

    def test_not_es_returns_original(self):
        assert i18n.translate("Product not found", "en") == "Product not found"


class TestHandlerIntegration:
    def test_get_current_user_401_locale(self, client):
        es = client.get("/api/auth/me", headers={"Accept-Language": "es-MX"})
        en = client.get("/api/auth/me")
        assert es.status_code == 401 and en.status_code == 401
        assert es.json()["detail"] == "No autenticado"
        assert en.json()["detail"] == "Not authenticated"
        assert es.headers.get("WWW-Authenticate") == "Bearer"

    def test_catalog_error_locale(self, client, admin_headers):
        es = client.get(
            "/api/catalog/pdf",
            headers={**admin_headers, "Accept-Language": "es-MX"},
            params={"format": "xlsx"},
        )
        en = client.get("/api/catalog/pdf", headers=admin_headers, params={"format": "xlsx"})
        assert es.status_code == 400 and en.status_code == 400
        assert es.json()["detail"] == "El parámetro format debe ser 'pdf', 'html' o 'csv'"
        assert en.json()["detail"] == "The 'format' parameter must be 'pdf', 'html' or 'csv'"

    def test_422_validation_locale(self, client, admin_headers):
        es = client.post(
            "/api/categories",
            headers={**admin_headers, "Accept-Language": "es-MX"},
            json={},
        )
        en = client.post("/api/categories", headers=admin_headers, json={})
        assert es.status_code == 422 and en.status_code == 422
        es_msgs = {e["msg"] for e in es.json()["detail"]}
        en_msgs = {e["msg"] for e in en.json()["detail"]}
        assert "Campo requerido" in es_msgs
        assert "Field required" in en_msgs


def _collect_details():
    """Yield (path, lineno, message, is_static) for every detail message.

    ``is_static`` is True for plain string literals (must be in
    ``TRANSLATIONS``); f-string messages are split into their constant parts
    and must only be Spanish-free (they are matched by ``PATTERNS``).
    """
    def is_httpexception(node):
        f = node.func
        if isinstance(f, ast.Name):
            return f.id == "HTTPException"
        return isinstance(f, ast.Attribute) and f.attr == "HTTPException"

    root = pathlib.Path(__file__).resolve().parent.parent / "app"
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            values = []
            if isinstance(node, ast.Call) and is_httpexception(node):
                values += node.args[1:]
                values += [kw.value for kw in node.keywords if kw.arg == "detail"]
            elif isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == "detail":
                        values.append(v)
            for value in values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    yield (str(path), node.lineno, value.value, True)
                elif isinstance(value, ast.JoinedStr):
                    for part in value.values:
                        if isinstance(part, ast.Constant) and isinstance(part.value, str):
                            yield (str(path), node.lineno, part.value, False)


class TestCanonicalMessages:
    def test_no_spanish_detail_messages(self):
        spanish = [
            f"{path}:{lineno}:{msg!r}"
            for path, lineno, msg, _ in _collect_details()
            if re.search(r"[áéíóúñ¿¡]", msg, re.I)
        ]
        assert not spanish, f"mensajes en español restantes: {spanish}"

    def test_static_details_are_covered(self):
        uncovered = [
            f"{path}:{lineno}:{msg!r}"
            for path, lineno, msg, is_static in _collect_details()
            if is_static and not i18n.covered(msg)
        ]
        assert not uncovered, f"mensajes sin traducción: {uncovered}"

    def test_success_detail_is_covered(self):
        assert i18n.covered("Password updated successfully")