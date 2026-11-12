from fastapi.testclient import TestClient

from integration_lab.mock_erp import app

client = TestClient(app)
HEADERS = {"X-API-Key": "dev-erp-key"}


def test_mock_erp_creates_supplier() -> None:
    response = client.post(
        "/erp/suppliers",
        content=(
            "<supplier><name>Fornecedor Exemplo</name>"
            "<document>12345678000199</document>"
            "<email>contato@exemplo.com</email></supplier>"
        ),
        headers={**HEADERS, "Content-Type": "application/xml"},
    )
    assert response.status_code == 201
    assert "<id>ERP-" in response.text


def test_mock_erp_rejects_invalid_document() -> None:
    response = client.post(
        "/erp/suppliers",
        content="<supplier><document>123</document></supplier>",
        headers={**HEADERS, "Content-Type": "application/xml"},
    )
    assert response.status_code == 422


def test_mock_erp_requires_api_key() -> None:
    response = client.post(
        "/erp/suppliers",
        content="<supplier><document>12345678000199</document></supplier>",
    )
    assert response.status_code == 401
