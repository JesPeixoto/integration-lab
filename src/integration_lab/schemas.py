import re

from pydantic import BaseModel, Field, field_validator


class SupplierIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    document: str = Field(min_length=14, max_length=18)
    email: str = Field(min_length=5, max_length=120)

    @field_validator("document")
    @classmethod
    def normalize_document(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) != 14:
            raise ValueError("document must contain 14 digits")
        return digits


class SupplierOut(BaseModel):
    integration_id: str
    status: str
    erp_id: str | None = None


class IntegrationStatus(BaseModel):
    integration_id: str
    status: str
    erp_id: str | None = None
    detail: str | None = None
