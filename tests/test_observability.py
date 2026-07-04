from changeguard_ai.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_request_id_header_is_added_to_response():
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


def test_request_id_header_is_preserved_when_provided():
    response = client.get("/health", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
