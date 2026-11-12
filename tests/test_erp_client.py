from collections.abc import Callable

import httpx
import pytest

from integration_lab.config import Settings
from integration_lab.erp_client import ErpClient
from integration_lab.errors import ErpUnavailableError, ErpValidationError
from integration_lab.schemas import SupplierIn

SUPPLIER = SupplierIn(
    name="Fornecedor Exemplo",
    document="12345678000199",
    email="contato@exemplo.com",
)


def _erp_client(
    transport: httpx.MockTransport,
    *,
    max_attempts: int = 3,
    retry_base_seconds: float = 0.0,
    sleep: Callable[[float], None] | None = None,
) -> ErpClient:
    settings = Settings(
        erp_base_url="http://erp.test",
        erp_api_key="erp-key",
        erp_max_attempts=max_attempts,
        erp_retry_base_seconds=retry_base_seconds,
        erp_retry_max_seconds=retry_base_seconds,
    )
    http_client = httpx.Client(
        transport=transport,
        base_url=settings.erp_base_url,
        headers={"X-API-Key": settings.erp_api_key},
    )
    return ErpClient(settings, client=http_client, sleep=sleep or (lambda _: None))


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

    erp = _erp_client(httpx.MockTransport(handler), max_attempts=1)
    with pytest.raises(ErpUnavailableError):
        erp.create_supplier(SUPPLIER)


def test_create_supplier_raises_on_invalid_xml() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, text="not xml")

    erp = _erp_client(httpx.MockTransport(handler), max_attempts=1)
    with pytest.raises(ErpUnavailableError):
        erp.create_supplier(SUPPLIER)


def test_retry_succeeds_after_transient_failure() -> None:
    calls: list[httpx.Request] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(500, text="<error><message>boom</message></error>")
        return httpx.Response(201, text="<supplier><id>ERP-0001</id></supplier>")

    erp = _erp_client(
        httpx.MockTransport(handler),
        retry_base_seconds=0.1,
        sleep=sleeps.append,
    )

    assert erp.create_supplier(SUPPLIER) == "ERP-0001"
    assert len(calls) == 2
    assert len(sleeps) == 1
    assert sleeps[0] >= 0.1


def test_retry_gives_up_after_max_attempts() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503, text="<error><message>down</message></error>")

    erp = _erp_client(httpx.MockTransport(handler), max_attempts=2)

    with pytest.raises(ErpUnavailableError):
        erp.create_supplier(SUPPLIER)

    assert len(calls) == 2


def test_retry_does_not_retry_4xx() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(422, text="<error><message>invalid</message></error>")

    erp = _erp_client(httpx.MockTransport(handler))

    with pytest.raises(ErpValidationError):
        erp.create_supplier(SUPPLIER)

    assert len(calls) == 1
