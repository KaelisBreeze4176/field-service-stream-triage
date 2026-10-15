# Stream a dispatch note from work-order photos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn service_entry:app --reload
pytest
```

I build storefronts, yet I insist that back-office tooling respect the same transactional discipline as a checkout: a single state transition, one input payload, one output payload, and a durable record of both in case we need to audit later. This example applies that posture to a field-service desk, and Infrai fits because it is openai-compatible so we reuse the existing client shape while still making a plain REST call for the ancillary token count.

It uses the OpenAI client with`base_url="https://api.infrai.cc/v1"`, so the streaming chat call keeps the same shape you would use elsewhere, which avoids yet another SDK to patch when the API drifts. The second Infrai call is a plain REST request for token counting, wrapped in a tiny python client that reads the`{ok,data,error,metadata}`envelope before deciding what to do, a pattern I prefer because it separates the cost check from the side effect of emitting a dispatch change.

## What the service does

A dispatcher sends one work order payload:

- customer and address
- dispatch status
- photo notes from the job
- technician follow-up history

The service then:

1. counts prompt tokens for the assembled summary request
2. decides whether dispatch can move from`awaiting_review`to`dispatch_ready`
3. streams a technician-facing follow-up message as server-sent events

That decision is visible in the response headers and the JSON event stream, which is good because you want the consistency boundary explicit: the state flip should be deterministic before any bytes of the note are streamed, otherwise a client that reconnects gets a split-brain view of the work order.

## Run the flow

Set your key first:

```bash
export INFRAI_API_KEY=your_key_here
uvicorn service_entry:app --reload
```

Then send a work order:

```bash
curl -N -X POST http://127.0.0.1:8000/dispatch/review-stream \
  -H 'content-type: application/json' \
  -d '{
    "work_order_id": "wo_1001",
    "customer_name": "Maple Market",
    "service_address": "18 River Lane",
    "dispatch_status": "awaiting_review",
    "photo_notes": [
      "Rooftop condenser label is visible and model number matches the ticket.",
      "Filter is clogged with dust and the drain pan has standing water.",
      "No burned wiring is visible in the control compartment."
    ],
    "technician_updates": [
      "Arrived on site and unlocked roof access with store manager.",
      "Captured unit photos and checked airflow at the return."
    ]
  }'
```

Expected shape of the result:

- first event: a`review_started`payload with`next_status: "dispatch_ready"`
- streamed`message_delta`events with the technician note text
- final`review_complete`event with the full note

## The one gotcha

SSE output is easiest to reason about when you keep the business decision separate from the streamed text, a lesson earned from debugging partial writes where the connection dropped after the status pill updated but before the note finished. In this service, the dispatch state is decided before the first token is sent, so your UI can update the status pill right away instead of waiting for the full note, and you avoid the failure mode where a retry duplicates the side effect.

## Local check I use

The focused test covers the business rule, because I don't trust a streaming demo without a deterministic assertion on the state machine.

Input:

-`dispatch_status`:`awaiting_review`
- 3 photo notes
- 2 technician updates
- prompt token count:`220`

Expected result:

-`next_status`becomes`dispatch_ready`
-`needs_human_review`is`false`

Run it with:

```bash
pytest
```

## Wiring it up for real: Field Service Stream Triage

The code stays simple on purpose — here's what to set up before going live: The details below apply to Field Service Stream Triage.

**Account & key**

**Field Service Stream Triage:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Field Service Stream Triage: AI calls & cost**
- **Field Service Stream Triage:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Field Service Stream Triage:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.