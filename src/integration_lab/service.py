from threading import Lock
from uuid import uuid4

from .erp_client import ErpClient
from .errors import IntegrationError
from .schemas import IntegrationStatus, SupplierIn


class IntegrationRepository:
    def __init__(self) -> None:
        self._records: dict[str, IntegrationStatus] = {}
        self._lock = Lock()

    def save(self, record: IntegrationStatus) -> None:
        with self._lock:
            self._records[record.integration_id] = record

    def get(self, integration_id: str) -> IntegrationStatus | None:
        with self._lock:
            return self._records.get(integration_id)


class IntegrationService:
    def __init__(self, erp_client: ErpClient, repository: IntegrationRepository) -> None:
        self._erp_client = erp_client
        self._repository = repository

    def create_supplier(self, supplier: SupplierIn) -> IntegrationStatus:
        integration_id = str(uuid4())
        self._repository.save(IntegrationStatus(integration_id=integration_id, status="pending"))

        try:
            erp_id = self._erp_client.create_supplier(supplier)
        except IntegrationError as exc:
            self._repository.save(
                IntegrationStatus(
                    integration_id=integration_id,
                    status="failed",
                    detail=exc.detail,
                )
            )
            raise

        record = IntegrationStatus(
            integration_id=integration_id,
            status="success",
            erp_id=erp_id,
        )
        self._repository.save(record)
        return record
