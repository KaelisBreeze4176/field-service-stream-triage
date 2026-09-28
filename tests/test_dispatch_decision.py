from dispatch_review_service import DispatchReviewService
from field_review_models import WorkOrderReviewRequest


class DummyTokensClient:
    def __init__(self):
        self.payload = None

    def ai_tokens_count(self, payload):
        self.payload = payload
        return {"total_tokens": 220}


class DummyAIClient:
    pass


def test_dispatch_moves_to_ready_when_photos_and_updates_are_present():
    tokens_client = DummyTokensClient()
    service = DispatchReviewService(tokens_client=tokens_client, ai_client=DummyAIClient())
    review = WorkOrderReviewRequest(
        work_order_id="wo_1001",
        customer_name="Maple Market",
        service_address="18 River Lane",
        dispatch_status="awaiting_review",
        photo_notes=[
            "Rooftop condenser label is visible and model number matches the ticket.",
            "Filter is clogged with dust and the drain pan has standing water.",
            "No burned wiring is visible in the control compartment.",
        ],
        technician_updates=[
            "Arrived on site and unlocked roof access with store manager.",
            "Captured unit photos and checked airflow at the return.",
        ],
    )

    prompt = service.build_prompt(review)
    prompt_tokens = service.count_prompt_tokens(prompt)
    assert tokens_client.payload == {"model": "auto", "messages": [{"role": "user", "content": prompt}]}
    decision = service.decide_dispatch(review, prompt_tokens)

    assert decision.next_status == "dispatch_ready"
    assert decision.needs_human_review is False
    assert decision.prompt_tokens == 220
