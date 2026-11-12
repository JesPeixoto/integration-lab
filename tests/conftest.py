from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from integration_lab.main import app, get_erp_client, get_repository
from integration_lab.service import IntegrationRepository
from tests.fakes import FakeErpClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    repository = IntegrationRepository()
    fake_erp = FakeErpClient()
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_erp_client] = lambda: fake_erp
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
