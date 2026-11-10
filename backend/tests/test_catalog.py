"""Conector de catálogo: el bot responde precio y stock desde la API del negocio."""
import urllib.error
from unittest.mock import patch

import pytest
from django.test import override_settings

from chat import catalog
from chat.models import Conversation
from tenants.models import BusinessDomain

pytestmark = pytest.mark.django_db

API = "https://tienda.example.com/api/products/"
ORIGIN = "https://tienda.example.com"
PRODUCTS = [
    {"name": "iPhone 15 256GB Chip", "price": "2790.00", "inventory": 0},
    {"name": "iPhone 15 128GB Chip", "price": "2490.00", "inventory": 2},
    {"name": "iPhone 15 Pro 128GB Natural (Seminuevo)", "price": "2990.00", "inventory": 1},
    {"name": "iPhone 16 128GB Chip", "price": "2890.00", "inventory": 2},
    {"name": "<script>alert(1)</script>", "price": "1", "inventory": 1},
]
NO_MATCH = {"answer": "Lo derivo a un asesor.", "category": None, "matched": False, "escalate": True}
FAQ_MATCH = {"answer": "Respuesta de FAQ.", "category": "garantias", "matched": True, "escalate": False}

allowed = override_settings(CATALOG_ALLOWED_HOSTS=["tienda.example.com"])


@pytest.fixture
def shop(pilot):
    BusinessDomain.objects.create(business=pilot, origin=ORIGIN)
    pilot.chatbot.catalog_api_url = API
    pilot.chatbot.catalog_page_url = "https://tienda.example.com/catalogo"
    pilot.chatbot.save()
    return pilot


def widget_say(api, business, text, reply):
    headers = {"HTTP_ORIGIN": ORIGIN}
    token = api.post(f"/api/widget/{business.public_id}/session/", {}, format="json", **headers).json()["token"]
    with patch("chat.conversation.ask_chatbot", return_value=reply):
        return api.post(
            f"/api/widget/{business.public_id}/messages/", {"message": text}, format="json",
            HTTP_X_VISITOR_TOKEN=token, **headers,
        )


# ---------------------------------------------------------------- seguridad de la URL

@allowed
@pytest.mark.parametrize("url", [
    "https://interno.example.com/api/",       # host fuera de la lista blanca
    "http://169.254.169.254/latest/meta-data/",  # metadatos de la nube (SSRF)
    "http://localhost:8000/api/",
    "https://user:pw@tienda.example.com/api/",
    "ftp://tienda.example.com/api/",
    "tienda.example.com/api/",
])
def test_catalog_url_must_be_an_allowed_http_host(url):
    with pytest.raises(catalog.CatalogUrlNotAllowed):
        catalog.validate_catalog_url(url)


@allowed
def test_allowed_host_passes():
    assert catalog.validate_catalog_url(API) == API


def test_redirects_are_not_followed():
    handler = catalog._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", {}, "http://169.254.169.254/") is None


@allowed
def test_panel_rejects_a_catalog_host_that_is_not_allowed(admin_api):
    bad = admin_api.patch(
        "/api/business/", {"chatbot": {"catalog_api_url": "http://169.254.169.254/x"}}, format="json"
    )
    assert bad.status_code == 400
    good = admin_api.patch("/api/business/", {"chatbot": {"catalog_api_url": API}}, format="json")
    assert good.status_code == 200


# ---------------------------------------------------------------- búsqueda

@allowed
def test_search_filters_by_product_words_and_sorts_available_first():
    with patch("chat.catalog._fetch", return_value=PRODUCTS) as fetch:
        result = catalog.search(API, "¿Cuánto cuesta el iPhone 15?")
    assert fetch.call_args.args[0] == API + "?search=iphone"
    names = [p["name"] for p in result["products"]]
    # Solo modelos "iphone 15"; primero lo disponible y, dentro, el más barato.
    assert names == ["iPhone 15 128GB Chip", "iPhone 15 Pro 128GB Natural (Seminuevo)", "iPhone 15 256GB Chip"]
    assert result["products"][2]["available"] is False


@allowed
def test_search_returns_none_when_the_catalog_fails():
    with patch("chat.catalog._fetch", side_effect=urllib.error.URLError("caído")):
        assert catalog.search(API, "iphone 15") is None


def test_search_ignores_questions_without_product_words():
    assert catalog.search(API, "¿cuánto cuesta?") is None


def test_answer_lists_real_prices_and_stock():
    text = catalog.format_answer(
        "Black Dog Store",
        [{"name": "iPhone 15 128GB Chip", "price": catalog._price("2490.00"), "available": True},
         {"name": "iPhone 15 256GB Chip", "price": catalog._price("2790.00"), "available": False}],
        4,
        "https://tienda.example.com/catalogo",
    )
    assert "iPhone 15 128GB Chip — S/ 2,490.00 — disponible" in text
    assert "iPhone 15 256GB Chip — S/ 2,790.00 — agotado" in text
    assert "(y 2 opciones más)" in text and "asesor" in text
    assert text.endswith("Ver catálogo: https://tienda.example.com/catalogo")


# ---------------------------------------------------------------- en la conversación

@allowed
def test_widget_answers_from_catalog_instead_of_escalating(api, shop):
    with patch("chat.catalog._fetch", return_value=PRODUCTS):
        response = widget_say(api, shop, "iPhone 15", NO_MATCH)
    body = response.json()
    assert response.status_code == 201
    assert body["escalated"] is False
    assert "iPhone 15 128GB Chip — S/ 2,490.00 — disponible" in body["bot_message"]["content"]
    assert Conversation.objects.get().status == "abierta"


@allowed
def test_faq_has_priority_over_catalog(api, shop):
    with patch("chat.catalog._fetch") as fetch:
        response = widget_say(api, shop, "¿Tienen garantía el iPhone 15?", FAQ_MATCH)
    assert response.json()["bot_message"]["content"] == "Respuesta de FAQ."
    fetch.assert_not_called()


@allowed
def test_catalog_failure_keeps_the_previous_escalation(api, shop):
    with patch("chat.catalog._fetch", side_effect=TimeoutError()):
        response = widget_say(api, shop, "iPhone 15", NO_MATCH)
    assert response.json()["escalated"] is True
    assert Conversation.objects.get().status == "derivada"


@allowed
def test_no_catalog_configured_means_no_lookup(api, pilot):
    BusinessDomain.objects.create(business=pilot, origin=ORIGIN)
    with patch("chat.catalog._fetch") as fetch:
        widget_say(api, pilot, "iPhone 15", NO_MATCH)
    fetch.assert_not_called()



@allowed
def test_same_name_products_are_told_apart_by_their_detail():
    items = [
        {"name": "iPhone 15 Pro 128GB (Seminuevo)", "price": "2990", "inventory": 1,
         "description": "eSIM · Batería 100%. Equipo seminuevo."},
        {"name": "iPhone 15 Pro 128GB (Seminuevo)", "price": "2990", "inventory": 1,
         "description": "eSIM · Batería 97%. Equipo seminuevo."},
    ]
    with patch("chat.catalog._fetch", return_value=items):
        names = [p["name"] for p in catalog.search(API, "iphone 15")["products"]]
    assert sorted(names) == [
        "iPhone 15 Pro 128GB (Seminuevo) · eSIM · Batería 100%",
        "iPhone 15 Pro 128GB (Seminuevo) · eSIM · Batería 97%",
    ]
