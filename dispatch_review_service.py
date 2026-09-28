from openai import OpenAI

from field_review_models import DispatchDecision, WorkOrderReviewRequest
from infrai_client import InfraiClient


class DispatchReviewService:
    def __init__(self, tokens_client: InfraiClient, ai_client: OpenAI):
        self.tokens_client = tokens_client
        self.ai_client = ai_client

    def build_prompt(self, review: WorkOrderReviewRequest) -> str:
        photo_block = "\n".join(f"- {note}" for note in review.photo_notes)
        update_block = "\n".join(f"- {note}" for note in review.technician_updates) or "- No technician updates yet"
        return (
            f"Work order: {review.work_order_id}\n"
            f"Customer: {review.customer_name}\n"
            f"Address: {review.service_address}\n"
            f"Dispatch status: {review.dispatch_status}\n"
            f"Photo notes:\n{photo_block}\n"
            f"Technician updates:\n{update_block}\n"
            "Write a concise follow-up note for the technician. Mention the observed issue, "
            "the next onsite action, and a customer-safe status line."
        )

    def count_prompt_tokens(self, prompt: str) -> int:
        data = self.tokens_client.ai_tokens_count({"model": "auto", "messages": [{"role": "user", "content": prompt}]})
        value = data.get("total_tokens")
        if isinstance(value, int):
            return value
        if isinstance(data.get("count"), int):
            return int(data["count"])
        raise ValueError("Token count response did not include an integer token total")

    def decide_dispatch(self, review: WorkOrderReviewRequest, prompt_tokens: int) -> DispatchDecision:
        has_enough_photo_context = len(review.photo_notes) >= 2
        has_recent_field_update = len(review.technician_updates) >= 1
        if review.dispatch_status == "awaiting_review" and has_enough_photo_context and has_recent_field_update and prompt_tokens <= 500:
            return DispatchDecision(
                next_status="dispatch_ready",
                needs_human_review=False,
                decision_reason="Sufficient photo context and technician notes for dispatcher handoff.",
                prompt_tokens=prompt_tokens,
            )
        return DispatchDecision(
            next_status="needs_follow_up",
            needs_human_review=True,
            decision_reason="Dispatcher should request one more technician update before scheduling the next step.",
            prompt_tokens=prompt_tokens,
        )

    def stream_technician_message(self, review: WorkOrderReviewRequest):
        prompt = self.build_prompt(review)
        return self.ai_client.chat.completions.create(
            model="auto",
            stream=True,
            messages=[
                {
                    "role": "system",
                    "content": "You write brief technician follow-up notes for a field-service dispatcher UI.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
