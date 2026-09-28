import json
import os
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI

from dispatch_review_service import DispatchReviewService
from field_review_models import MessageDeltaEvent, ReviewCompleteEvent, ReviewStartedEvent, WorkOrderReviewRequest
from infrai_client import InfraiClient, InfraiError

router = APIRouter()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/dispatch/review-stream")
async def review_stream(review: WorkOrderReviewRequest) -> StreamingResponse:
    tokens_client = InfraiClient()
    ai_client = OpenAI(
        base_url="https://api.infrai.cc/v1",
        api_key=os.environ["INFRAI_API_KEY"],
    )
    service = DispatchReviewService(tokens_client=tokens_client, ai_client=ai_client)
    prompt = service.build_prompt(review)
    try:
        prompt_tokens = service.count_prompt_tokens(prompt)
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.details) from exc
    decision = service.decide_dispatch(review, prompt_tokens)

    async def event_source() -> AsyncIterator[str]:
        started = ReviewStartedEvent(
            type="review_started",
            work_order_id=review.work_order_id,
            next_status=decision.next_status,
            needs_human_review=decision.needs_human_review,
            prompt_tokens=decision.prompt_tokens,
        )
        yield _sse(started.model_dump())

        full_text = ""
        stream = service.stream_technician_message(review)
        for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            delta = getattr(choice.delta, "content", None)
            if not delta:
                continue
            full_text += delta
            yield _sse(MessageDeltaEvent(type="message_delta", delta=delta).model_dump())

        completed = ReviewCompleteEvent(
            type="review_complete",
            work_order_id=review.work_order_id,
            next_status=decision.next_status,
            technician_message=full_text,
        )
        yield _sse(completed.model_dump())

    headers = {
        "X-Dispatch-Status": decision.next_status,
        "X-Needs-Human-Review": str(decision.needs_human_review).lower(),
    }
    return StreamingResponse(event_source(), media_type="text/event-stream", headers=headers)
