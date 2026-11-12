from collections.abc import Iterator
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx
from fastapi import Depends

from .config import Settings, get_settings
from .errors import ErpUnavailableError, ErpValidationError
from .schemas import SupplierIn


class ErpClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            base_url=settings.erp_base_url,
            timeout=settings.erp_timeout_seconds,
            headers={"X-API-Key": settings.erp_api_key},
        )

    def close(self) -> None:
        self._client.close()

    def create_supplier(self, supplier: SupplierIn) -> str:
        xml = self._to_xml(supplier)
        try:
            response = self._client.post(
                "/erp/suppliers",
                content=xml,
                headers={"Content-Type": "application/xml"},
            )
        except httpx.TimeoutException as exc:
            raise ErpUnavailableError("ERP timed out") from exc
        except httpx.HTTPError as exc:
            raise ErpUnavailableError(f"ERP request failed: {exc}") from exc

        if response.status_code >= 500:
            raise ErpUnavailableError(f"ERP returned HTTP {response.status_code}")
        if response.status_code >= 400:
            raise ErpValidationError(self._extract_error(response.text))

        return self._parse_id(response.text)

    @staticmethod
    def _to_xml(supplier: SupplierIn) -> str:
        root = Element("supplier")
        SubElement(root, "name").text = supplier.name
        SubElement(root, "document").text = supplier.document
        SubElement(root, "email").text = supplier.email
        return tostring(root, encoding="unicode")

    @staticmethod
    def _parse_id(xml_text: str) -> str:
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            raise ErpUnavailableError("ERP returned invalid XML") from exc
        erp_id = root.findtext("id")
        if not erp_id:
            raise ErpUnavailableError("ERP response is missing the supplier id")
        return erp_id

    @staticmethod
    def _extract_error(xml_text: str) -> str:
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            return "ERP rejected the payload"
        return root.findtext("message") or "ERP rejected the payload"


def get_erp_client(settings: Settings = Depends(get_settings)) -> Iterator[ErpClient]:
    client = ErpClient(settings)
    try:
        yield client
    finally:
        client.close()
