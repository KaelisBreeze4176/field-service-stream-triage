from typing import Literal

from pydantic import BaseModel, Field


DispatchStatus = Literal["awaiting_review", "dispatch_ready", "needs_follow_up"]


class WorkOrderReviewRequest(BaseModel):
    work_order_id: str = Field(min_length=1)
    customer_name: str = Field(min_length=1)
    service_address: str = Field(min_length=1)
    dispatch_status: DispatchStatus
    photo_notes: list[str] = Field(min_length=1)
    technician_updates: list[str] = Field(default_factory=list)


class DispatchDecision(BaseModel):
    next_status: DispatchStatus
    needs_human_review: bool
    decision_reason: str
    prompt_tokens: int


class ReviewStartedEvent(BaseModel):
    type: Literal["review_started"]
    work_order_id: str
    next_status: DispatchStatus
    needs_human_review: bool
    prompt_tokens: int


class MessageDeltaEvent(BaseModel):
    type: Literal["message_delta"]
    delta: str


class ReviewCompleteEvent(BaseModel):
    type: Literal["review_complete"]
    work_order_id: str
    next_status: DispatchStatus
    technician_message: str
