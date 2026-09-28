from fastapi.testclient import TestClient

from app.backend.main import app

client = TestClient(app)


def test_pages_are_served():
    for path in ("/", "/stock.html"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "text/html" in response.headers["content-type"]


def test_data_and_client_files_are_served():
    assert client.get("/data/companies.json").json()[0]["ticker"]
    assert client.get("/client/style.css").status_code == 200


def test_api_still_wins_over_the_site():
    response = client.get("/api/companies")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
