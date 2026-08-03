from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import make_pdf_bytes

client = TestClient(app)


def test_manual_upload_uses_pdf_extractor() -> None:
    response = client.post(
        "/api/documents/extract-upload",
        files={
            "file": ("announcement.pdf", make_pdf_bytes(["Uploaded filing"]), "application/pdf")
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Uploaded filing" in response.json()["pages"][0]["text"]


def test_manual_upload_rejects_non_pdf() -> None:
    response = client.post(
        "/api/documents/extract-upload",
        files={"file": ("not-pdf.html", b"<html></html>", "text/html")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_pdf"
