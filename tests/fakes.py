from integration_lab.schemas import SupplierIn


class FakeErpClient:
    def __init__(self, erp_id: str = "ERP-0001", error: Exception | None = None) -> None:
        self.erp_id = erp_id
        self.error = error
        self.calls: list[SupplierIn] = []

    def create_supplier(self, supplier: SupplierIn) -> str:
        self.calls.append(supplier)
        if self.error is not None:
            raise self.error
        return self.erp_id

    def close(self) -> None:
        pass


class FlakyErpClient(FakeErpClient):
    def __init__(self, failures: int, error: Exception, erp_id: str = "ERP-0001") -> None:
        super().__init__(erp_id=erp_id)
        self.failures = failures
        self.error = error

    def create_supplier(self, supplier: SupplierIn) -> str:
        self.calls.append(supplier)
        if self.failures > 0:
            self.failures -= 1
            raise self.error
        return self.erp_id
