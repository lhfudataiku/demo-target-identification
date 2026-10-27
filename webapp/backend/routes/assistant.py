"""Act 4 — the evidence assistant for the selected pair (redesign D1, workplan Phase 7a).

  POST /api/assistant   one question about one pair, answered as a stream of server-sent events

The body is {disease, gene, question, history}; history is the conversation so far, held by the page,
because nothing is stored here. Events, one JSON object per `data:` line:

  text_delta           the answer as it is written
  tool_call_started    a search began (name, args)
  tool_call_completed  it ended (ok, summary; graph results carry their id)
  answer               the checked answer: sentences with resolved citations, general-knowledge and
                       prescriptive flags, and every graph result with its Cypher
  error                the turn failed

Streamed with FastAPI's own StreamingResponse, so no SSE library is needed.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services import assistant

router = APIRouter(prefix="/api/assistant")


class Turn(BaseModel):
    role: str
    content: str


class Ask(BaseModel):
    disease: int
    gene: int
    question: str = Field(min_length=1, max_length=2000)
    history: list[Turn] = []


def _sse(events: Iterator[dict]) -> Iterator[str]:
    for e in events:
        yield f"data: {json.dumps(e, default=str)}\n\n"


@router.post("")
def ask(body: Ask) -> StreamingResponse:
    events = assistant.answer(body.disease, body.gene, body.question, [t.model_dump() for t in body.history])
    return StreamingResponse(_sse(events), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
