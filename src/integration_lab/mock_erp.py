from itertools import count
from xml.etree import ElementTree

from fastapi import FastAPI, Header, HTTPException, Request, Response

from .config import get_settings

app = FastAPI(title="Mock ERP", version="0.1.0")
settings = get_settings()
_sequence = count(1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/erp/suppliers", status_code=201)
async def create_supplier(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> Response:
    if x_api_key != settings.erp_api_key:
        raise HTTPException(status_code=401, detail="Invalid ERP API key")

    if request.headers.get("X-Simulate-Failure") == "true":
        return Response(
            "<error><message>simulated ERP failure</message></error>",
            status_code=500,
            media_type="application/xml",
        )

    body = await request.body()
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return Response(
            "<error><message>invalid XML</message></error>",
            status_code=422,
            media_type="application/xml",
        )

    document = root.findtext("document") or ""
    if len(document) != 14 or not document.isdigit():
        return Response(
            "<error><message>document must contain 14 digits</message></error>",
            status_code=422,
            media_type="application/xml",
        )

    erp_id = f"ERP-{next(_sequence):04d}"
    xml = f"<supplier><id>{erp_id}</id><status>created</status></supplier>"
    return Response(xml, status_code=201, media_type="application/xml")
