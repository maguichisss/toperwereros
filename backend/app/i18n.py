"""Lightweight message localization for API errors.

Canonical messages live in English in the routers. When a request asks for
Spanish via ``Accept-Language``, an exception handler swaps ``detail`` for the
localized version defined here; unknown messages fall back to English.

Cero drift rule: every message raised by the routers must be covered by
``TRANSLATIONS`` (exact) or ``PATTERNS`` (interpolated) - enforced by
``tests/test_i18n.py``.
"""

import re

from fastapi import Request

SUPPORTED_LANGS = ("en", "es")


def negotiate_lang(request: Request) -> str:
    header = (request.headers.get("accept-language") or "").lower()
    first = header.split(",")[0].strip().split(";")[0]
    return "es" if first.startswith("es") else "en"


TRANSLATIONS = {
    # app/auth.py
    "Not authenticated": "No autenticado",
    "Invalid token": "Token inválido",
    "User not found or inactive": "Usuario no encontrado o inactivo",
    "You do not have permission to perform this action": "No tienes permiso para realizar esta acción",
    # app/config.py
    "Invalid image path": "Ruta de imagen inválida",
    # app/query_filters.py
    "The 'modo' parameter must be 'basico' or 'detallado'": "El parámetro modo debe ser 'basico' o 'detallado'",
    # app/routers/auth.py
    "Incorrect username or password": "Usuario o contraseña incorrectos",
    "Inactive user": "Usuario inactivo",
    "Invalid refresh token": "Token de refresco inválido",
    "Revoked refresh token": "Token de refresco revocado",
    "Expired refresh token": "Token de refresco expirado",
    "A role with that name already exists": "El nombre del rol ya existe",
    "Error creating role": "Error al crear el rol",
    "Current password is incorrect": "Contraseña actual incorrecta",
    "The new password must be at least 4 characters long": "La nueva contraseña debe tener al menos 4 caracteres",
    "Error changing password": "Error al cambiar la contraseña",
    "Password updated successfully": "Contraseña actualizada correctamente",
    "Email already registered by another user": "El email ya está registrado por otro usuario",
    "Error updating profile": "Error al actualizar el perfil",
    "File too large (max 5MB)": "Archivo demasiado grande (máx 5MB)",
    "Invalid image file": "Archivo de imagen inválido",
    "Only JPEG, PNG and WebP images are allowed": "Solo se permiten imágenes JPEG, PNG y WebP",
    "Error uploading avatar": "Error al subir el avatar",
    "Username already exists": "El nombre de usuario ya existe",
    "Email already registered": "El email ya está registrado",
    "Error registering user": "Error al registrar el usuario",
    "User not found": "Usuario no encontrado",
    "You cannot change your own role": "No puedes cambiar tu propio rol",
    "You cannot deactivate your own account": "No puedes desactivar tu propia cuenta",
    "Error updating user": "Error al actualizar el usuario",
    "The 'active' field is required": "El campo 'active' es requerido",
    "Error updating user status": "Error al actualizar el estado del usuario",
    # app/routers/catalog.py
    "The 'format' parameter must be 'pdf', 'html' or 'csv'": "El parámetro format debe ser 'pdf', 'html' o 'csv'",
    "The 'ids' parameter must contain only numbers": "El parámetro ids debe contener solo números",
    "Error generating the PDF catalog": "Error al generar el catálogo PDF",
    # app/routers/categories.py
    "Name is required": "El nombre es obligatorio",
    "Category already exists": "La categoría ya fue creada",
    "Error creating category": "Error al crear la categoría",
    "Category not found": "Categoría no encontrada",
    "Error updating category": "Error al actualizar la categoría",
    "Cannot delete a category assigned to products": "No se puede eliminar una categoría asignada a productos",
    "Error deleting category": "Error al eliminar la categoría",
    # app/routers/colors.py
    "The hex color must be in #RRGGBB format": "El color hexadecimal debe tener formato #RRGGBB",
    "Error creating color": "Error al crear el color",
    "Color not found": "Color no encontrado",
    "Error updating color": "Error al actualizar el color",
    "Cannot delete a color assigned to products": "No se puede eliminar un color asignado a productos",
    "Error deleting color": "Error al eliminar el color",
    # app/routers/customers.py
    "Customer not found": "Cliente no encontrado",
    "Error creating customer": "Error al crear el cliente",
    "Error updating customer": "Error al actualizar el cliente",
    "Error deleting customer": "Error al eliminar el cliente",
    # app/routers/layaways.py
    "The layaway must have at least one item": "El apartado debe tener al menos un artículo",
    "Provide either customer_id or customer, not both": "Proporcione customer_id o customer, no ambos",
    "Provide an existing customer or create a new one": "Debe proporcionar un cliente existente o crear uno nuevo",
    "The deposit must be greater than zero": "El depósito debe ser mayor a cero",
    "The deposit cannot exceed the total": "El depósito no puede exceder el total",
    "Error creating layaway": "Error al crear el apartado",
    "Error fetching layaways": "Error al obtener los apartados",
    "Error fetching layaway": "Error al obtener el apartado",
    "Layaway not found": "Apartado no encontrado",
    "Only active layaways can be edited": "Solo se pueden editar apartados activos",
    "Error updating layaway": "Error al actualizar el apartado",
    "Payments can only be added to active layaways": "Solo se pueden agregar abonos a apartados activos",
    "The payment must be greater than zero": "El abono debe ser mayor a cero",
    "Error registering payment": "Error al registrar el abono",
    "Only active layaways can be modified": "Solo se pueden modificar apartados activos",
    "Error adding item to layaway": "Error al agregar el artículo al apartado",
    "Item not found in this layaway": "Artículo no encontrado en este apartado",
    "The layaway must have at least one item. Use 'cancel' to remove all.": "El apartado debe tener al menos un artículo. Use cancelar para eliminar todos.",
    "Error removing item from layaway": "Error al eliminar el artículo del apartado",
    "Error updating layaway item": "Error al actualizar el artículo del apartado",
    "Only active layaways can be cancelled": "Solo se pueden cancelar apartados activos",
    "Error cancelling layaway": "Error al cancelar el apartado",
    "Only active layaways can be completed": "Solo se pueden completar apartados activos",
    "Error completing layaway": "Error al completar el apartado",
    # app/routers/products.py
    "Product not found": "Producto no encontrado",
    "Code is required": "El código es obligatorio",
    "Price must be valid": "El precio debe ser válido",
    "One or more categories were not found": "Una o más categorías no fueron encontradas",
    "One or more colors were not found": "Uno o más colores no fueron encontrados",
    "Error creating product": "Error al crear el producto",
    "Error updating product": "Error al actualizar el producto",
    "Error deleting product": "Error al eliminar el producto",
    # app/routers/sales.py
    "Error fetching sales": "Error al obtener las ventas",
    "Error fetching sale": "Error al obtener la venta",
    "Sale not found": "Venta no encontrada",
    "The sale must have at least one item": "La venta debe tener al menos un artículo",
    "Error processing sale. Stock not deducted.": "Error al procesar la venta. Stock no descontado.",
    # app/routers/upload.py
    "Error uploading image": "Error al subir la imagen",
    # Pydantic/framework (used by the 422 handler)
    "Field required": "Campo requerido",
    "Input should be a valid integer": "Debe ser un número entero válido",
    "Input should be a valid number": "Debe ser un número válido",
    "String should have at least 4 characters": "Debe tener al menos 4 caracteres",
}

_VERB_MOVE_PATTERN = re.compile(
    r"^Cannot (remove|reduce): the new total \(\$([\d.]+)\) would be less than the payments made \(\$([\d.]+)\)$"
)
_CANNOT_VERBS = {"remove": "eliminar", "reduce": "reducir"}

PATTERNS = [
    (re.compile(r"^Invalid value for filter (.+?): '(.*)' \(use true/false\)$"),
     "Valor inválido para el filtro {0}: '{1}' (use true/false)"),
    (re.compile(r"^Invalid value for filter (.+?): '(.*)'$"),
     "Valor inválido para el filtro {0}: '{1}'"),
    (re.compile(r"^Filter (.+?) requires at least one value$"),
     "El filtro {0} requiere al menos un valor"),
    (re.compile(r"^Unknown filter parameter: (.+)$"),
     "Parámetro de filtro desconocido: {0}"),
    (re.compile(r"^The operator '(.+?)' only applies to text fields$"),
     "El operador '{0}' solo aplica a campos de texto"),
    (re.compile(r"^Unknown filter operator: (.+)$"),
     "Operador de filtro desconocido: {0}"),
    (re.compile(r"^Non-selectable projection field: (.+)$"),
     "Campo de proyección no seleccionable: {0}"),
    (re.compile(r"^Product (\d+) not found$"),
     "Producto {0} no encontrado"),
    (re.compile(r"^Insufficient stock for '([^']+)': (\d+) available, (\d+) requested$"),
     "Stock insuficiente para '{0}': {1} disponible(s), {2} solicitado(s)"),
    (re.compile(r"^Insufficient stock for '([^']+)': (\d+) available, (\d+) additional requested$"),
     "Stock insuficiente para '{0}': {1} disponible(s), {2} adicional(es) solicitado(s)"),
    (re.compile(r"^Payment exceeds the pending balance: \$(.+)$"),
     "El abono excede el saldo pendiente: ${0}"),
    (_VERB_MOVE_PATTERN,
     lambda verb, new_total, payments: f"No se puede {_CANNOT_VERBS[verb]}: el nuevo total (${new_total}) sería menor que los abonos realizados (${payments})"),
    (re.compile(r"^A product with code '(.+)' already exists$"),
     "Ya existe un producto con ese código: '{0}'"),
    (re.compile(r"^A color named '(.+)' already exists$"),
     "El color '{0}' ya existe"),
    (re.compile(r"^The 'theme' parameter must be one of: (.+)$"),
     "El parámetro theme debe ser uno de: {0}"),
]


def translate(message: str, lang: str) -> str:
    if lang != "es":
        return message
    if message in TRANSLATIONS:
        return TRANSLATIONS[message]
    for pattern, template in PATTERNS:
        match = pattern.fullmatch(message)
        if match:
            if callable(template):
                return template(*match.groups())
            return template.format(*match.groups())
    return message


def exact_covered(message: str) -> bool:
    return message in TRANSLATIONS


def pattern_covered(message: str) -> bool:
    return any(pattern.fullmatch(message) for pattern, _ in PATTERNS)


def covered(message: str) -> bool:
    return exact_covered(message) or pattern_covered(message)