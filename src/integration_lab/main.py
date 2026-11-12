from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.security import APIKeyHeader

from .config import Settings, get_settings
from .erp_client import ErpClient, get_erp_client
from .errors import IntegrationError, integration_error_handler
from .logging import configure_logging, request_id_var
from .schemas import IntegrationStatus, SupplierIn, SupplierOut
from .service import IntegrationRepository, IntegrationService

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="Integration Lab", version="0.1.0")
app.add_exception_handler(IntegrationError, integration_error_handler)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_repository = IntegrationRepository()


def get_repository() -> IntegrationRepository:
    return _repository


def get_service(
    erp_client: ErpClient = Depends(get_erp_client),
    repository: IntegrationRepository = Depends(get_repository),
) -> IntegrationService:
    return IntegrationService(erp_client, repository)


def require_api_key(
    api_key: str | None = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(
    supplier: SupplierIn,
    response: Response,
    _: None = Depends(require_api_key),
    service: IntegrationService = Depends(get_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SupplierOut:
    record = service.create_supplier(supplier, idempotency_key)
    if idempotency_key:
        response.headers["Idempotency-Key"] = idempotency_key
    return SupplierOut(
        integration_id=record.integration_id,
        status=record.status,
        erp_id=record.erp_id,
    )


@app.get("/api/v1/integrations/{integration_id}", response_model=IntegrationStatus)
def get_integration(
    integration_id: str,
    _: None = Depends(require_api_key),
    repository: IntegrationRepository = Depends(get_repository),
) -> IntegrationStatus:
    record = repository.get(integration_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    return record
