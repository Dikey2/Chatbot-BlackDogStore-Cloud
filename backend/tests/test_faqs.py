import pytest

from faqs.models import FAQ

pytestmark = pytest.mark.django_db
URL = "/api/faqs/"

NEW = {
    "category": "garantias",
    "question": "¿Hay garantía?",
    "answer": "DATO FICTICIO: 12 meses.",
    "keywords": "garantía, devolución",
}


def detail(faq):
    return f"{URL}{faq.id}/"


# ---------- lectura ----------
def test_list_is_public_and_paginated(api, faq):
    response = api.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert set(body) == {"count", "next", "previous", "results"}
    assert body["results"][0]["question"] == faq.question


def test_list_pagination_page_size_20(api, db):
    FAQ.objects.bulk_create(
        FAQ(category="c", question=f"p{i}", answer="r", keywords="k") for i in range(25)
    )
    first = api.get(URL).json()
    assert (first["count"], len(first["results"])) == (25, 20)
    assert len(api.get(URL, {"page": 2}).json()["results"]) == 5
    assert api.get(URL, {"page": 99}).status_code == 404


def test_list_filters_by_category(api, faq):
    FAQ.objects.create(category="otra", question="q", answer="a", keywords="k")
    results = api.get(URL, {"category": "horarios"}).json()["results"]
    assert [r["id"] for r in results] == [faq.id]


def test_inactive_faq_hidden_from_public_and_cliente_but_visible_to_admin(
    api, cliente_api, admin_api, faq
):
    faq.is_active = False
    faq.save()
    assert api.get(URL).json()["count"] == 0
    assert cliente_api.get(URL).json()["count"] == 0
    assert api.get(detail(faq)).status_code == 404
    assert admin_api.get(URL).json()["count"] == 1


def test_retrieve(api, faq):
    response = api.get(detail(faq))
    assert response.status_code == 200
    assert response.json()["answer"] == faq.answer


def test_retrieve_missing_gives_404_json(api, db):
    response = api.get(f"{URL}9999/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# ---------- escritura ----------
def test_admin_creates(admin_api):
    response = admin_api.post(URL, NEW, format="json")
    assert response.status_code == 201
    assert response.json()["is_active"] is True
    assert FAQ.objects.get().question == NEW["question"]


def test_admin_updates_and_patches(admin_api, faq):
    response = admin_api.put(detail(faq), {**NEW, "is_active": False}, format="json")
    assert response.status_code == 200
    faq.refresh_from_db()
    assert (faq.category, faq.is_active) == ("garantias", False)

    response = admin_api.patch(detail(faq), {"answer": "Nueva"}, format="json")
    assert response.status_code == 200
    faq.refresh_from_db()
    assert faq.answer == "Nueva"


def test_admin_deletes(admin_api, faq):
    assert admin_api.delete(detail(faq)).status_code == 204
    assert not FAQ.objects.exists()


@pytest.mark.parametrize(
    "override, field",
    [
        ({"question": ""}, "question"),
        ({"keywords": " , "}, "keywords"),
        ({"category": "x" * 51}, "category"),
    ],
)
def test_create_validates(admin_api, override, field):
    response = admin_api.post(URL, {**NEW, **override}, format="json")
    assert response.status_code == 400
    assert field in response.json()["error"]["fields"]
    assert not FAQ.objects.exists()


# ---------- permisos por rol ----------
def test_anonymous_cannot_write(api, faq):
    assert api.post(URL, NEW, format="json").status_code == 401
    assert api.patch(detail(faq), {"answer": "x"}, format="json").status_code == 401
    assert api.delete(detail(faq)).status_code == 401
    assert FAQ.objects.get().answer == faq.answer


@pytest.mark.parametrize("client_fixture", ["cliente_api", "asesor_api"])
def test_cliente_and_asesor_cannot_write(request, client_fixture, faq):
    client = request.getfixturevalue(client_fixture)
    for response in (
        client.post(URL, NEW, format="json"),
        client.put(detail(faq), NEW, format="json"),
        client.patch(detail(faq), {"answer": "x"}, format="json"),
        client.delete(detail(faq)),
    ):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"
    assert FAQ.objects.get().answer == faq.answer
