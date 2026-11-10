"""Conector de catálogo: el bot consulta productos en la API del propio negocio.

Así el asistente responde precio y disponibilidad con los datos de la tienda EN
ESE MOMENTO, sin copiarlos a FAQ ni inventarlos.

Seguridad (la URL la configura el administrador del negocio, por eso se trata
como entrada no confiable):
- Solo http(s) y solo hosts de ``settings.CATALOG_ALLOWED_HOSTS`` (evita que la
  plataforma consulte direcciones internas: SSRF).
- No se siguen redirecciones (una redirección podría llevar a otro host).
- Solo GET, timeout corto y respuesta de 1 MB como máximo.
- De la respuesta solo se leen nombre, precio y stock; nada se ejecuta ni se muestra como HTML.

Contrato esperado de la API: ``GET <url>?search=<texto>`` devuelve una lista (o
``{"results": [...]}``) de objetos con ``name``, ``price`` y ``inventory`` /
``available_stock`` / ``in_stock``.
"""
import json
import logging
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

from django.conf import settings

logger = logging.getLogger("chat.catalog")

TIMEOUT_SECONDS = 2.5
MAX_BYTES = 1_000_000
MAX_RESULTS = 6

# Palabras de la pregunta que no describen el producto.
STOPWORDS = {
    "a", "al", "algun", "alguna", "alguno", "busco", "buscando", "cual", "cuales", "cuanto", "cuanta",
    "cuesta", "cuestan", "de", "del", "disponible", "disponibles", "el", "en", "es", "esta", "estan",
    "hay", "hola", "la", "las", "lo", "los", "me", "mi", "modelo", "modelos", "necesito", "o", "para",
    "por", "precio", "precios", "que", "quiero", "quisiera", "saber", "se", "stock", "su", "sus",
    "tiene", "tienen", "tienes", "un", "una", "unos", "unas", "valor", "vale", "venden", "y", "favor",
    "interesa", "informacion", "equipo", "equipos", "comprar", "consulta", "consultar",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


class CatalogUrlNotAllowed(ValueError):
    pass


def validate_catalog_url(value):
    """URL permitida para el conector, o CatalogUrlNotAllowed."""
    if not value:
        return value
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise CatalogUrlNotAllowed("Indique una URL http(s) completa.")
    if parts.username or parts.password:
        raise CatalogUrlNotAllowed("La URL no puede incluir usuario ni contraseña.")
    if parts.hostname.lower() not in settings.CATALOG_ALLOWED_HOSTS:
        raise CatalogUrlNotAllowed(
            "Ese host no está autorizado para el conector de catálogo. "
            "Pida al superadministrador que lo agregue a CATALOG_ALLOWED_HOSTS."
        )
    return value


def _words(text):
    text = unicodedata.normalize("NFD", (text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", text)


def product_terms(message):
    """Palabras de la pregunta que describen el producto ("iphone", "15", "pro")."""
    return [w for w in _words(message) if w not in STOPWORDS][:6]


def _fetch(url):
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with _opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("respuesta demasiado grande")
    data = json.loads(raw)
    return data.get("results", []) if isinstance(data, dict) else data


def _available(item):
    for key in ("available_stock", "inventory"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return value > 0
    if isinstance(item.get("in_stock"), bool):
        return item["in_stock"]
    return None


def _price(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def search(url, message):
    """{"products": [...], "total": n} con lo que coincide, o None si no aplica o falla."""
    terms = product_terms(message)
    if not url or not terms:
        return None
    try:
        validate_catalog_url(url)
    except CatalogUrlNotAllowed:
        return None
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query) + [("search", terms[0])]
    full = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))
    started = time.monotonic()
    try:
        items = _fetch(full)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        logger.warning(
            "catalog_unavailable",
            extra={
                "operation": "catalog.search",
                "error": type(exc).__name__,
                "duration_ms": round((time.monotonic() - started) * 1000, 1),
            },
        )
        return None
    wanted = set(terms)
    found = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        if not wanted <= set(_words(item["name"])):
            continue
        found.append({
            "name": item["name"][:120],
            "price": _price(item.get("price")),
            "available": _available(item),
            "detail": _first_sentence(item.get("description")),
        })
    # Primero lo disponible y, dentro de cada grupo, de menor a mayor precio.
    found.sort(key=lambda p: (p["available"] is not True, p["price"] or Decimal("Infinity")))
    products = found[:MAX_RESULTS]
    # Dos equipos con el mismo nombre (p. ej. seminuevos con distinta batería): se distinguen.
    names = [p["name"] for p in products]
    for p in products:
        if names.count(p["name"]) > 1 and p["detail"]:
            p["name"] = f"{p['name']} · {p['detail']}"
    return {"products": products, "total": len(found)}


def _first_sentence(text):
    if not isinstance(text, str):
        return ""
    first = text.strip().split(".")[0].strip()
    return first if 0 < len(first) <= 60 else ""


def format_answer(business_name, products, total_hint, page_url=""):
    lines = [f"Esto encontré ahora en el catálogo de {business_name}:"]
    for p in products:
        price = f"S/ {p['price']:,.2f}" if p["price"] is not None else "precio a consultar"
        state = {True: "disponible", False: "agotado", None: "consultar stock"}[p["available"]]
        lines.append(f"• {p['name']} — {price} — {state}")
    if total_hint > len(products):
        lines.append(f"(y {total_hint - len(products)} opciones más)")
    lines.append("Precios y stock según el catálogo en este momento. ¿Quieres que un asesor te lo confirme o reserve?")
    if page_url:
        lines.append(f"Ver catálogo: {page_url}")
    return "\n".join(lines)
