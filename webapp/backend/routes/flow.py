"""Flow block — Vue Flow node/edge graph example.

GET /api/flow/sample  returns a small directed graph (4 nodes, 3 edges).

Node positions (x/y) are baked in so no layout library is needed for the
hello-world.  To auto-layout large graphs, compute positions on the frontend
with @dagrejs/dagre — keep the backend model position-free in that case.

This route is intentionally **self-contained** (no DSS) so the block renders
with zero configuration.  To make it real, replace the static graph with e.g.
a DSS project's flow (project.get_flow() via the Python API) or any domain
graph structure you want to visualise.

Optional block — registered only when ENABLE_FLOW=1 (see backend/app.py).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/flow")


class FlowNode(BaseModel):
    id: str
    label: str
    node_type: str
    x: float
    y: float
    owner: Optional[str] = None
    queue_count: Optional[int] = None
    sla: Optional[str] = None
    note: Optional[str] = None


class FlowEdge(BaseModel):
    id: str
    source: str
    target: str


class FlowSample(BaseModel):
    nodes: list[FlowNode]
    edges: list[FlowEdge]


@router.get("/sample", response_model=FlowSample)
def sample_flow() -> FlowSample:
    """Return a sample pipeline graph for the Flow view.

    This represents a medical-information intake flow:
    Incoming Tickets → Triage → Medical Information / Other Teams → Closed.
    Replace with your domain graph (DSS project flow, dependency tree, etc.).
    """
    return FlowSample(
        nodes=[
            FlowNode(
                id="1",
                label="Incoming Tickets",
                node_type="source",
                x=40,
                y=120,
                owner="Medical Information Inbox",
                queue_count=42,
                sla="New intake every 15 min",
                note="Doctors ask about dose, storage, compatibility, and patient events.",
            ),
            FlowNode(
                id="2",
                label="Triage",
                node_type="transform",
                x=250,
                y=120,
                owner="MI coordinators",
                queue_count=18,
                sla="Median first look: 1.2 h",
                note="Confirms whether the ticket belongs with MI or another function.",
            ),
            FlowNode(
                id="3",
                label="Medical Information",
                node_type="enrich",
                x=470,
                y=40,
                owner="Scientific response team",
                queue_count=24,
                sla="91% within SLA",
                note="Scientific questions stay here for response drafting and approval.",
            ),
            FlowNode(
                id="4",
                label="Other Teams",
                node_type="reroute",
                x=470,
                y=205,
                owner="Safety / Quality / Access",
                queue_count=11,
                sla="Reroute in < 30 min",
                note="Adverse events, product complaints, and reimbursement questions are redirected.",
            ),
            FlowNode(
                id="5",
                label="Closed",
                node_type="output",
                x=705,
                y=120,
                owner="Completed",
                queue_count=33,
                sla="Same day when possible",
                note="Answered or accepted by the receiving team.",
            ),
        ],
        edges=[
            FlowEdge(id="e1-2", source="1", target="2"),
            FlowEdge(id="e2-3", source="2", target="3"),
            FlowEdge(id="e2-4", source="2", target="4"),
            FlowEdge(id="e3-5", source="3", target="5"),
            FlowEdge(id="e4-5", source="4", target="5"),
        ],
    )
