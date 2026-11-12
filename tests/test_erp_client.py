import httpx
import pytest

from integration_lab.config import Settings
from integration_lab.erp_client import ErpClient
from integration_lab.errors import ErpUnavailableError
from integration_lab.schemas import SupplierIn

SUPPLIER = SupplierIn(
    name="Fornecedor Exemplo",
    document="12345678000199",
    email="contato@exemplo.com",
)


def _erp_client(transport: httpx.MockTransport) -> ErpClient:
    settings = Settings(erp_base_url="http://erp.test", erp_api_key="erp-key")
    http_client = httpx.Client(
        transport=transport,
        base_url=settings.erp_base_url,
        headers={"X-API-Key": settings.erp_api_key},
    )
    return ErpClient(settings, client=http_client)


def test_create_supplier_sends_xml_and_parses_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "erp-key"
        assert request.headers["Content-Type"] == "application/xml"
        body = request.content.decode()
        assert "<name>Fornecedor Exemplo</name>" in body
        assert "<document>12345678000199</document>" in body
        return httpx.Response(201, text="<supplier><id>ERP-0001</id></supplier>")

    erp = _erp_client(httpx.MockTransport(handler))
    assert erp.create_supplier(SUPPLIER) == "ERP-0001"


def test_create_supplier_raises_on_erp_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="<error><message>boom</message></error>")

    erp = _erp_client(httpx.MockTransport(handler))
    with pytest.raises(ErpUnavailableError):
        erp.create_supplier(SUPPLIER)


def test_create_supplier_raises_on_invalid_xml() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, text="not xml")

    erp = _erp_client(httpx.MockTransport(handler))
    with pytest.raises(ErpUnavailableError):
        erp.create_supplier(SUPPLIER)
