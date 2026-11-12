from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from uuid import uuid4

from .erp_client import ErpClient
from .errors import IdempotencyConflictError, IdempotencyInProgressError, IntegrationError
from .schemas import IntegrationStatus, SupplierIn


@dataclass
class IdempotencyRecord:
    payload_hash: str
    state: str = "in_progress"
    integration: IntegrationStatus | None = None


class IntegrationRepository:
    def __init__(self) -> None:
        self._records: dict[str, IntegrationStatus] = {}
        self._idempotency: dict[str, IdempotencyRecord] = {}
        self._lock = Lock()

    def save(self, record: IntegrationStatus) -> None:
        with self._lock:
            self._records[record.integration_id] = record

    def get(self, integration_id: str) -> IntegrationStatus | None:
        with self._lock:
            return self._records.get(integration_id)

    def begin_idempotent(self, key: str, payload_hash: str) -> tuple[IdempotencyRecord, bool]:
        with self._lock:
            existing = self._idempotency.get(key)
            if existing is not None:
                if existing.payload_hash != payload_hash:
                    raise IdempotencyConflictError(
                        "Idempotency-Key was reused with a different payload"
                    )
                return existing, False
            record = IdempotencyRecord(payload_hash=payload_hash)
            self._idempotency[key] = record
            return record, True

    def complete_idempotent(self, key: str, integration: IntegrationStatus) -> None:
        with self._lock:
            record = self._idempotency.get(key)
            if record is not None:
                record.state = "completed"
                record.integration = integration

    def release_idempotent(self, key: str) -> None:
        with self._lock:
            self._idempotency.pop(key, None)


class IntegrationService:
    def __init__(self, erp_client: ErpClient, repository: IntegrationRepository) -> None:
        self._erp_client = erp_client
        self._repository = repository

    def create_supplier(
        self,
        supplier: SupplierIn,
        idempotency_key: str | None = None,
    ) -> IntegrationStatus:
        if idempotency_key:
            record, created = self._repository.begin_idempotent(
                idempotency_key,
                self._payload_hash(supplier),
            )
            if not created:
                if record.state == "completed" and record.integration is not None:
                    return record.integration
                raise IdempotencyInProgressError(
                    "A request with this Idempotency-Key is already in progress"
                )

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
            if idempotency_key:
                self._repository.release_idempotent(idempotency_key)
            raise

        record = IntegrationStatus(
            integration_id=integration_id,
            status="success",
            erp_id=erp_id,
        )
        self._repository.save(record)
        if idempotency_key:
            self._repository.complete_idempotent(idempotency_key, record)
        return record

    @staticmethod
    def _payload_hash(supplier: SupplierIn) -> str:
        return sha256(supplier.model_dump_json().encode("utf-8")).hexdigest()
