import dagre from "@dagrejs/dagre";
import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

const NODE_W = 200;
const NODE_H = 74;

export function layout(
  nodes: FlowNode[],
  edges: FlowEdge[],
  direction: "TB" | "LR" = "TB",
): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 28, ranksep: 56, marginx: 12, marginy: 12 });

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);

  const laidOut = nodes.map((n) => {
    const p = g.node(n.id);
    return {
      ...n,
      position: { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 },
      targetPosition: direction === "LR" ? "left" : "top",
      sourcePosition: direction === "LR" ? "right" : "bottom",
    } as FlowNode;
  });

  return { nodes: laidOut, edges };
}
