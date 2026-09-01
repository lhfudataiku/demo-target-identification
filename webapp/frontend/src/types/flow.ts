// Types for the Flow building block — mirrors backend/routes/flow.py models.

export interface FlowNode {
  id: string
  label: string
  node_type: string
  x: number
  y: number
  owner?: string | null
  queue_count?: number | null
  sla?: string | null
  note?: string | null
}

export interface FlowEdge {
  id: string
  source: string
  target: string
}

export interface FlowSample {
  nodes: FlowNode[]
  edges: FlowEdge[]
}
