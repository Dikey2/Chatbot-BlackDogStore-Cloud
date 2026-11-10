"""Motor de reglas: busca las palabras clave de cada FAQ en el mensaje del cliente.

El servicio no guarda contenido. La API principal envía en cada consulta las FAQ
activas que administra (RF-04, RF-07).

Cada negocio envía su configuración (``settings``): nombre, nombre del asistente,
mensaje sin respuesta, mensaje y palabras de derivación. Sin ella se usan textos
neutros; el servicio nunca inventa datos comerciales.

Orden de decisión:
0. Regla de derivación del negocio (por ejemplo, "quiero hablar con un asesor").
1. FAQ con más palabras clave coincidentes.
2. Conversación básica (saludo, agradecimiento, despedida, ayuda), solo si el
   mensaje no contiene nada más.
3. Derivación a un asesor (RF-09).
"""
import re
import unicodedata

FALLBACK = (
    "No tengo información confirmada sobre esa consulta. "
    "La derivaré a un asesor para su revisión."
)

# Frases de conversación básica, ya normalizadas (minúsculas, sin tildes).
SMALL_TALK = {
    "saludo": [
        "hola", "holi", "buenos dias", "buen dia", "buenas tardes", "buenas noches",
        "buenas", "saludos", "que tal", "hey",
    ],
    "agradecimiento": ["gracias", "muchas gracias", "mil gracias", "te agradezco", "le agradezco"],
    "despedida": ["adios", "chau", "chao", "hasta luego", "hasta pronto", "nos vemos"],
    "ayuda": [
        "ayuda", "ayudame", "ayudeme", "necesito ayuda", "que puedes hacer",
        "que haces", "opciones", "menu", "en que me puedes ayudar",
    ],
}

# Palabras que no aportan contenido: "hola, buenos días a todos" sigue siendo un saludo.
FILLER = {
    "a", "al", "de", "del", "el", "la", "las", "los", "lo", "y", "e", "por", "favor",
    "muy", "un", "una", "todos", "todas", "senor", "senora", "senorita", "amigo", "amiga",
    "bot", "asistente", "me", "te", "le", "tu", "usted", "ustedes", "pues", "bueno", "ok",
}

DEFAULT_ASSISTANT = "el asistente virtual"
DEFAULT_HANDOFF = "Listo. Un asesor revisará tu consulta y te responderá por este chat."


def _greeting(settings):
    business = (settings or {}).get("business_name", "").strip()
    assistant = (settings or {}).get("assistant_name", "").strip() or DEFAULT_ASSISTANT
    return f"¡Hola! Soy {assistant}{f' de {business}' if business and business not in assistant else ''}."


GREETING = _greeting({"business_name": "Black Dog Store"})


def normalize_text(text):
    """Minúsculas, sin tildes ni signos; palabras separadas por un espacio."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def normalize(text):
    """Conjunto de palabras normalizadas."""
    return set(normalize_text(text).split())


def _topics(faqs):
    categories = sorted({faq["category"] for faq in faqs})
    if not categories:
        return "Por ahora no tengo temas configurados; un asesor puede atenderte."
    return "Puedo ayudarte con: " + ", ".join(categories) + ". ¿Qué deseas consultar?"


def small_talk(message, faqs, settings=None):
    """Categoría y respuesta si el mensaje es solo conversación básica; si no, None."""
    text = f" {normalize_text(message)} "
    found = []
    # Frases largas primero, para que "muchas gracias" no deje "muchas" suelto.
    phrases = sorted(
        ((phrase, category) for category, items in SMALL_TALK.items() for phrase in items),
        key=lambda item: -len(item[0]),
    )
    for phrase, category in phrases:
        if f" {phrase} " in text:
            text = text.replace(f" {phrase} ", " ")
            found.append(category)
    if not found or set(text.split()) - FILLER:
        return None

    if "ayuda" in found or "saludo" in found:
        answer = f"{_greeting(settings) if settings else GREETING} {_topics(faqs)}"
        category = "ayuda" if "ayuda" in found else "saludo"
    elif "agradecimiento" in found:
        answer, category = "¡Con gusto! Si tienes otra consulta, escríbeme.", "agradecimiento"
    else:
        business = (settings or {}).get("business_name", "Black Dog Store").strip()
        answer = f"¡Hasta pronto! Gracias por escribir{f' a {business}' if business else ''}."
        category = "despedida"
    return category, answer


def wants_handoff(message, keywords):
    text = f" {normalize_text(message)} "
    return any(f" {normalize_text(k)} " in text for k in keywords if normalize_text(k))


def find_reply(message, faqs, settings=None):
    """Devuelve la FAQ con más palabras clave, conversación básica o derivación (RF-09)."""
    settings = settings or {}
    if wants_handoff(message, settings.get("handoff_keywords") or []):
        return {
            "answer": settings.get("handoff_message") or DEFAULT_HANDOFF,
            "category": "derivacion",
            "matched": True,
            "escalate": True,
        }
    words = normalize(message)
    best, best_score = None, 0
    for faq in faqs:
        keywords = set().union(*(normalize(k) for k in faq["keywords"]))
        score = len(words & keywords)
        if score > best_score:
            best, best_score = faq, score
    if best is not None:
        return {
            "answer": best["answer"],
            "category": best["category"],
            "matched": True,
            "escalate": False,
        }

    talk = small_talk(message, faqs, settings or None)
    if talk is not None:
        category, answer = talk
        return {"answer": answer, "category": category, "matched": True, "escalate": False}

    fallback = settings.get("no_answer_message") or FALLBACK
    return {"answer": fallback, "category": None, "matched": False, "escalate": True}
