"""Motor de reglas: busca las palabras clave de cada FAQ en el mensaje del cliente.

El servicio no guarda contenido. La API principal envía en cada consulta las FAQ
activas que administra (RF-04, RF-07).
"""
import re
import unicodedata

FALLBACK = (
    "No tengo información confirmada sobre esa consulta. "
    "La derivaré a un asesor para su revisión."
)


def normalize(text):
    """Minúsculas, sin tildes, separado en palabras."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return set(re.findall(r"[a-z0-9]+", text))


def find_reply(message, faqs):
    """Devuelve la FAQ con más palabras clave coincidentes, o derivación (RF-09)."""
    words = normalize(message)
    best, best_score = None, 0
    for faq in faqs:
        keywords = set().union(*(normalize(k) for k in faq["keywords"]))
        score = len(words & keywords)
        if score > best_score:
            best, best_score = faq, score
    if best is None:
        return {"answer": FALLBACK, "category": None, "matched": False, "escalate": True}
    return {
        "answer": best["answer"],
        "category": best["category"],
        "matched": True,
        "escalate": False,
    }
