from fastapi.testclient import TestClient

from integration_lab.errors import ErpUnavailableError
from integration_lab.main import app, get_erp_client
from tests.fakes import FakeErpClient, FlakyErpClient

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


def test_idempotency_same_key_returns_same_result(
    client: TestClient,
    fake_erp: FakeErpClient,
) -> None:
    headers = {**HEADERS, "Idempotency-Key": "supplier-123"}
    first = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=headers)
    second = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()
    assert len(fake_erp.calls) == 1


def test_idempotency_same_key_different_payload_returns_409(client: TestClient) -> None:
    headers = {**HEADERS, "Idempotency-Key": "supplier-456"}
    first = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=headers)
    assert first.status_code == 201

    second = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "name": "Outro Fornecedor"},
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["title"] == "Idempotency key conflict"


def test_idempotency_failure_releases_key(client: TestClient) -> None:
    flaky = FlakyErpClient(failures=1, error=ErpUnavailableError("ERP down"))
    app.dependency_overrides[get_erp_client] = lambda: flaky
    headers = {**HEADERS, "Idempotency-Key": "supplier-789"}

    first = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=headers)
    assert first.status_code == 503

    second = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=headers)
    assert second.status_code == 201
    assert len(flaky.calls) == 2
