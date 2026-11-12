import logging
import random
import time
from collections.abc import Callable, Iterator
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx
from fastapi import Depends

from .config import Settings, get_settings
from .errors import ErpUnavailableError, ErpValidationError
from .schemas import SupplierIn

_log = logging.getLogger(__name__)


class ErpClient:
    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._client = client or httpx.Client(
            base_url=settings.erp_base_url,
            timeout=settings.erp_timeout_seconds,
            headers={"X-API-Key": settings.erp_api_key},
        )

    def close(self) -> None:
        self._client.close()

    def create_supplier(self, supplier: SupplierIn) -> str:
        xml = self._to_xml(supplier)
        max_attempts = self._settings.erp_max_attempts
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                response = self._client.post(
                    "/erp/suppliers",
                    content=xml,
                    headers={"Content-Type": "application/xml"},
                )
            except httpx.TimeoutException:
                last_error = ErpUnavailableError("ERP timed out")
            except httpx.TransportError as exc:
                last_error = ErpUnavailableError(f"ERP request failed: {exc}")
            else:
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = ErpUnavailableError(f"ERP returned HTTP {response.status_code}")
                elif response.status_code >= 400:
                    raise ErpValidationError(self._extract_error(response.text))
                else:
                    return self._parse_id(response.text)

            if attempt == max_attempts - 1:
                assert last_error is not None
                raise last_error

            _log.warning(
                "Transient ERP failure (attempt %d/%d): %s",
                attempt + 1,
                max_attempts,
                last_error,
            )
            self._sleep_before_retry(attempt)

        raise ErpUnavailableError("ERP request failed after retries")

    def _sleep_before_retry(self, attempt: int) -> None:
        delay = min(
            self._settings.erp_retry_base_seconds * (2**attempt),
            self._settings.erp_retry_max_seconds,
        )
        if delay > 0:
            delay += random.uniform(0, delay * 0.1)
        self._sleep(delay)

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
