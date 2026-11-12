from fastapi import Request
from fastapi.responses import JSONResponse


class IntegrationError(Exception):
    code = "integration_error"
    status_code = 500
    title = "Integration error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ErpUnavailableError(IntegrationError):
    code = "erp_unavailable"
    status_code = 503
    title = "ERP unavailable"


class ErpValidationError(IntegrationError):
    code = "erp_validation_error"
    status_code = 422
    title = "ERP rejected the payload"


class IdempotencyConflictError(IntegrationError):
    code = "idempotency_conflict"
    status_code = 409
    title = "Idempotency key conflict"


class IdempotencyInProgressError(IntegrationError):
    code = "idempotency_in_progress"
    status_code = 409
    title = "Request already in progress"


async def integration_error_handler(request: Request, exc: IntegrationError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://integration-lab.dev/errors/{exc.code}",
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": request.url.path,
        },
    )
