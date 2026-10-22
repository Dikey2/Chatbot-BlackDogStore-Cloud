import pytest

FAQS = [{"category": "garantias", "answer": "Garantía ficticia.", "keywords": ["garantía"]}]


def post(client, body):
    return client.post("/api/reply/", body, content_type="application/json")


def test_health(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "chatbot"}


def test_reply_ok(client):
    response = post(client, {"message": "¿Tienen garantía?", "faqs": FAQS})
    assert response.status_code == 200
    assert response.json()["category"] == "garantias"


def test_reply_with_empty_faq_list_escalates(client):
    response = post(client, {"message": "hola", "faqs": []})
    assert response.status_code == 200
    assert response.json()["escalate"] is True


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"message": "hola"},
        {"message": "   ", "faqs": []},
        {"message": "a" * 501, "faqs": []},
        {"message": "hola", "faqs": [{"category": "x"}]},
        {"message": "hola", "faqs": "no es lista"},
    ],
)
def test_reply_rejects_invalid_body(client, body):
    assert post(client, body).status_code == 400


def test_reply_rejects_get(client):
    assert client.get("/api/reply/").status_code == 405
