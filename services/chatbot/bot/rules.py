"""Motor de reglas: busca las palabras clave de cada FAQ en el mensaje del cliente.

El servicio no guarda contenido. La API principal envía en cada consulta las FAQ
activas que administra (RF-04, RF-07).

Orden de decisión:
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

GREETING = "¡Hola! Soy el asistente virtual de Black Dog Store."


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


def small_talk(message, faqs):
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
        answer = f"{GREETING} {_topics(faqs)}"
        category = "ayuda" if "ayuda" in found else "saludo"
    elif "agradecimiento" in found:
        answer, category = "¡Con gusto! Si tienes otra consulta, escríbeme.", "agradecimiento"
    else:
        answer, category = "¡Hasta pronto! Gracias por escribir a Black Dog Store.", "despedida"
    return category, answer


def find_reply(message, faqs):
    """Devuelve la FAQ con más palabras clave, conversación básica o derivación (RF-09)."""
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

    talk = small_talk(message, faqs)
    if talk is not None:
        category, answer = talk
        return {"answer": answer, "category": category, "matched": True, "escalate": False}

    return {"answer": FALLBACK, "category": None, "matched": False, "escalate": True}
