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
