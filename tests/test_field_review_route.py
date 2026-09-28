from unittest.mock import patch

from fastapi.testclient import TestClient

from infrai_client import InfraiError
from service_entry import app


def test_token_count_error_preserves_upstream_status(monkeypatch):
    monkeypatch.setenv("INFRAI_API_KEY", "test-key")
    details = {"code": "INVALID_ARGUMENT", "message": "bad messages"}
    with patch("field_review_route.DispatchReviewService.count_prompt_tokens", side_effect=InfraiError("INVALID_ARGUMENT", details, 400)):
        response = TestClient(app).post("/dispatch/review-stream", json={
            "work_order_id": "wo_1001",
            "customer_name": "Maple Market",
            "service_address": "18 River Lane",
            "dispatch_status": "awaiting_review",
            "photo_notes": ["Unit photographed"],
        })

    assert response.status_code == 400
    assert response.json() == {"detail": details}
