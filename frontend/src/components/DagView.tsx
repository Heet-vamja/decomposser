import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position,
  type Edge as FlowEdge,
  type Node as FlowNode,
  type NodeProps,
} from "reactflow";
import { layout } from "../lib/layout";
import type { DecompositionResult } from "../types";

function SubQueryNode({ data }: NodeProps) {
  return (
    <div className="rf-node" title={data.full}>
      <Handle type="target" position={Position.Top} />
      <div className="rf-id">
        {data.id}
        {data.role ? <span className="rf-badge role">{data.role}</span> : null}
      </div>
      <div>{data.label}</div>
      {data.tier ? <span className={`rf-badge ${data.tier}`}>{data.tier} model</span> : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { sq: SubQueryNode };

function truncate(s: string, n = 96) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export default function DagView({ result }: { result: DecompositionResult }) {
  const { nodes, edges } = useMemo(() => {
    const rawNodes: FlowNode[] = result.subqueries.map((s) => ({
      id: s.id,
      type: "sq",
      position: { x: 0, y: 0 },
      data: {
        id: s.id,
        label: truncate(s.text),
        full: s.text,
        role: s.role ?? null,
        tier: s.model_tier ?? null,
      },
    }));
    const rawEdges: FlowEdge[] = result.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.from,
      target: e.to,
      animated: false,
      style: { stroke: "#94a3b8" },
    }));
    return layout(rawNodes, rawEdges, "TB");
  }, [result]);

  if (result.subqueries.length === 0) {
    return <div className="text-sm text-muted italic p-4">No sub-queries to show.</div>;
  }

  return (
    <div style={{ height: 320 }} className="rounded-lg border border-slate-200 bg-slate-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnScroll
      >
        <Background color="#cbd5e1" gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
