
"""Consulta de solo lectura al catálogo público de Black Dog Store Demo."""

import json
import os
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

CATALOG_API_URL = os.environ.get(
    "DEMO_CATALOG_API_URL",
    "https://blackdog-store-demo-api.onrender.com/api/products/",
)

MAX_PRODUCTS = 200
MAX_RESPONSE_BYTES = 2_000_000


class CatalogUnavailable(Exception):
    """El catálogo no está disponible o respondió incorrectamente."""


def get_products():
    """Obtiene productos públicos sin acceder directamente a la base de datos."""
    request = urllib.request.Request(
        CATALOG_API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "BlackDogStore-DemoCatalog/1.0",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status != 200:
                raise CatalogUnavailable("Respuesta HTTP inesperada.")

            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise CatalogUnavailable("Respuesta demasiado grande.")

            data = json.loads(raw)

    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        OSError,
    ) as exc:
        raise CatalogUnavailable("No se pudo consultar el catálogo.") from exc

    if isinstance(data, dict):
        products = data.get("results")
    elif isinstance(data, list):
        products = data
    else:
        products = None

    if not isinstance(products, list):
        raise CatalogUnavailable("Formato de catálogo inválido.")

    return [product for product in products[:MAX_PRODUCTS] if isinstance(product, dict)]


def public_product_data(product):
    """Extrae únicamente información comercial pública."""
    try:
        price = Decimal(str(product.get("price")))
        if not price.is_finite() or price < 0:
            price = None
    except (InvalidOperation, TypeError, ValueError):
        price = None

    inventory = product.get("inventory")
    if type(inventory) is not int or inventory < 0:
        inventory = None

    category = product.get("category") or {}

    return {
        "name": str(product.get("name") or ""),
        "description": str(product.get("description") or ""),
        "price": str(price) if price is not None else None,
        "inventory": inventory,
        "category": category.get("name", "") if isinstance(category, dict) else "",
        "condition": product.get("condition_line"),
        "slug": str(product.get("slug") or ""),
    }
