from bot.rules import find_reply, normalize

FAQS = [
    {"category": "horarios", "answer": "Horario ficticio.", "keywords": ["horario", "atención"]},
    {"category": "garantias", "answer": "Garantía ficticia.", "keywords": ["garantía", "devolución", "cambio"]},
]


def test_normalize_strips_accents_and_punctuation():
    assert normalize("¿Garantía? Sí.") == {"garantia", "si"}


def test_matches_ignoring_accents_and_case():
    result = find_reply("¿Cuál es el HORARIO de atencion?", FAQS)
    assert result == {
        "answer": "Horario ficticio.",
        "category": "horarios",
        "matched": True,
        "escalate": False,
    }


def test_keywords_with_accents_match_message_without_accents():
    assert find_reply("tienen garantia", FAQS)["category"] == "garantias"


def test_picks_faq_with_most_keywords():
    result = find_reply("Quiero la garantía para una devolución, ¿en qué horario?", FAQS)
    assert result["category"] == "garantias"


def test_unknown_question_escalates_to_advisor():
    result = find_reply("¿Cuánto cuesta la laptop X?", FAQS)
    assert result["matched"] is False
    assert result["escalate"] is True
    assert result["category"] is None


def test_keyword_must_be_whole_word():
    assert find_reply("intercambio de ideas", FAQS)["matched"] is False


def test_no_faqs_always_escalates():
    assert find_reply("horario", [])["escalate"] is True


# ---------- conversación básica ----------
import pytest  # noqa: E402


@pytest.mark.parametrize(
    "message",
    ["Buenos dias", "Buenos días", "¡Hola!", "hola, buenas tardes", "Buenas noches a todos", "holi"],
)
def test_greeting_is_answered_without_escalating(message):
    result = find_reply(message, FAQS)
    assert result["category"] == "saludo"
    assert result["escalate"] is False
    assert result["answer"].startswith("¡Hola! Soy el asistente virtual")
    assert "garantias, horarios" in result["answer"]


@pytest.mark.parametrize("message", ["gracias", "Muchas gracias!", "mil gracias, amigo"])
def test_thanks(message):
    result = find_reply(message, FAQS)
    assert (result["category"], result["escalate"]) == ("agradecimiento", False)


@pytest.mark.parametrize("message", ["adiós", "chau", "Hasta luego"])
def test_goodbye(message):
    result = find_reply(message, FAQS)
    assert (result["category"], result["escalate"]) == ("despedida", False)


@pytest.mark.parametrize("message", ["ayuda", "¿Qué puedes hacer?", "menú"])
def test_help_lists_faq_categories(message):
    result = find_reply(message, FAQS)
    assert result["category"] == "ayuda"
    assert "Puedo ayudarte con: garantias, horarios." in result["answer"]


def test_help_without_faqs_does_not_invent_topics():
    result = find_reply("hola", [])
    assert result["escalate"] is False
    assert "no tengo temas configurados" in result["answer"]


def test_faq_wins_over_greeting():
    result = find_reply("Buenos días, ¿cuál es el horario?", FAQS)
    assert result["category"] == "horarios"


def test_greeting_with_unknown_question_still_escalates():
    result = find_reply("Hola, ¿cuánto cuesta la laptop X?", FAQS)
    assert result["escalate"] is True
    assert result["category"] is None


def test_greeting_word_inside_other_word_is_not_a_greeting():
    # "chaleco" contiene "chao" a medias y "holanda" contiene "hola".
    assert find_reply("holanda", FAQS)["escalate"] is True
    assert find_reply("chaleco", FAQS)["escalate"] is True
