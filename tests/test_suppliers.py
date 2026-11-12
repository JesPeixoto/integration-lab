from fastapi.testclient import TestClient

from integration_lab.errors import ErpUnavailableError
from integration_lab.main import app, get_erp_client
from tests.fakes import FakeErpClient

VALID_SUPPLIER = {
    "name": "Fornecedor Exemplo",
    "document": "12345678000199",
    "email": "contato@exemplo.com",
}
HEADERS = {"X-API-Key": "dev-api-key"}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_supplier_success(client: TestClient) -> None:
    response = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=HEADERS)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["erp_id"] == "ERP-0001"
    assert body["integration_id"]


def test_create_supplier_requires_api_key(client: TestClient) -> None:
    response = client.post("/api/v1/suppliers", json=VALID_SUPPLIER)
    assert response.status_code == 401


def test_create_supplier_validates_document(client: TestClient) -> None:
    response = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "document": "123"},
        headers=HEADERS,
    )
    assert response.status_code == 422


def test_create_supplier_returns_503_when_erp_is_down(client: TestClient) -> None:
    app.dependency_overrides[get_erp_client] = lambda: FakeErpClient(
        error=ErpUnavailableError("ERP timed out")
    )
    response = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["title"] == "ERP unavailable"


def test_get_integration_status(client: TestClient) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=HEADERS).json()
    response = client.get(f"/api/v1/integrations/{created['integration_id']}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
