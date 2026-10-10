'use client';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export default function WorkflowGraph({ workflow }: { workflow: { nodes: { id: string; type: string; parameters?: object }[]; connections: [string, string][] } }) {
  const nodes: Node[] = workflow.nodes.map((n, i) => ({ id: n.id, position: { x: (i % 3) * 250, y: Math.floor(i / 3) * 150 }, data: { label: `${n.type.replaceAll('_', ' ')}\n${n.id}` }, style: { background: '#211848', color: '#fff', border: '1px solid #8d72dc', borderRadius: 14, padding: 12, minWidth: 150, whiteSpace: 'pre-line' } }));
  const edges: Edge[] = workflow.connections.map(([source, target], i) => ({ id: String(i), source, target, animated: false, style: { stroke: '#8e77d6', strokeWidth: 2 } }));
  return <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}><Background color="#c8bee0" /><Controls showInteractive={false} /></ReactFlow>;
}
