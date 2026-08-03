from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_company_search_endpoint() -> None:
    response = client.get("/api/companies/search", params={"q": "infosys"})

    assert response.status_code == 200
    assert response.json()["items"][0]["symbol"] == "INFY"


def test_company_search_rejects_empty_query() -> None:
    response = client.get("/api/companies/search", params={"q": ""})

    assert response.status_code == 422
