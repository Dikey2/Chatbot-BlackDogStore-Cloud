
"""Respuestas comerciales basadas en el catálogo público de demostración."""

import re
import unicodedata

from .catalog_client import CatalogUnavailable, get_products, public_product_data


def normalize(text):
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(
        char for char in text if unicodedata.category(char) != "Mn"
    )
    return " ".join(re.findall(r"[a-z0-9]+", text))


CATALOG_TERMS = (
    "precio", "cuanto cuesta", "cuanto vale", "costos",
    "catalogo", "productos", "disponible", "disponibilidad",
    "stock", "tienen", "venden", "comprar", "busco",
    "iphone", "ipad", "macbook", "airpods", "apple watch",
    "seminiuevo", "seminuevos", "nuevo", "nuevos",
)

STOPWORDS = {
    "que", "cual", "cuanto", "cuantos", "cuesta", "vale",
    "precio", "precios", "tienen", "tiene", "hay",
    "disponible", "disponibles", "stock", "busco", "quiero",
    "un", "una", "el", "la", "los", "las", "de", "del",
    "en", "por", "para", "me", "puedes", "mostrar",
    "productos", "producto", "catalogo", "comprar",
}


def is_catalog_question(message):
    text = normalize(message)
    return any(term in text for term in CATALOG_TERMS)


def catalog_reply(message):
    """Devuelve una respuesta comercial o None si no es una consulta de catálogo."""
    if not is_catalog_question(message):
        return None

    try:
        products = [public_product_data(p) for p in get_products()]
    except CatalogUnavailable:
        return {
            "answer": (
                "No puedo confirmar los productos ni sus precios en este momento. "
                "Inténtalo nuevamente o consulta con un asesor."
            ),
            "category": "catalogo",
            "matched": False,
            "escalate": False,
        }

    text = normalize(message)

    if "seminuevo" in text or "seminuevos" in text:
        products = [p for p in products if p["condition"] == "used"]
    elif "nuevo" in text or "nuevos" in text:
        products = [p for p in products if p["condition"] == "new"]

    terms = [
        term for term in text.split()
        if term not in STOPWORDS and len(term) > 1
    ]

    if terms:
        matches = [
            p for p in products
            if all(term in normalize(p["name"]) for term in terms)
        ]
    else:
        matches = products

    if not matches:
        answer = (
            "No encontré productos que coincidan con tu consulta "
            "en el catálogo de demostración. Puedes consultar con un asesor."
        )
    else:
        lines = ["Estos son algunos productos del catálogo de demostración:"]
        for product in matches[:5]:
            price = (
                f"S/ {product['price']}"
                if product["price"] is not None
                else "Precio no confirmado"
            )
            inventory = product["inventory"]
            availability = (
                f"{inventory} unidad(es) registrada(s)"
                if inventory is not None
                else "Disponibilidad no confirmada"
            )
            lines.append(
                f"- {product['name']}: {price}. {availability}."
            )

        lines.append(
            "Precios y existencias sujetos a cambios. "
            "Confirma la disponibilidad antes de comprar."
        )
        answer = "\n".join(lines)

    return {
        "answer": answer,
        "category": "catalogo",
        "matched": bool(matches),
        "escalate": False,
    }

