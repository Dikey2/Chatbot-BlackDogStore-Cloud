from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db
URL = "/api/health/"


@patch("core.views._chatbot_ok", return_value=True)
def test_ok_when_dependencies_respond(_, api):
    response = api.get(URL)
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "backend",
        "checks": {"database": "ok", "chatbot": "ok"},
    }


@patch("core.views._chatbot_ok", return_value=False)
def test_503_when_chatbot_is_down(_, api):
    response = api.get(URL)
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "chatbot": "error"}


@patch("core.views._chatbot_ok", return_value=True)
@patch("core.views._database_ok", return_value=False)
def test_503_when_database_is_down(_db, _bot, api):
    response = api.get(URL)
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "error"


def test_rejects_post(api):
    assert api.post(URL).status_code == 405


@patch("core.views._chatbot_ok", return_value=True)
def test_health_is_not_rate_limited(_, api, settings):
    for _i in range(70):  # por encima del límite anónimo de 60/min
        assert api.get(URL).status_code == 200
