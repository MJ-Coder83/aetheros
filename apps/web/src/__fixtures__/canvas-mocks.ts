/** Canvas mock data fixtures for testing.
 *
 * This file contains mock generators for testing Domain Canvas functionality.
 * Do not import in production code - use only in test files.
 */

import type { CanvasNode, CanvasEdge } from "@/types/canvas";
import type {
  CopilotSuggestion,
  SimulationMetric,
  TapeEventEntry,
  CanvasVersion,
} from "@/types/canvas-v5";

/** Generate mock canvas nodes for testing. */
export function generateMockNodes(): CanvasNode[] {
  return [
    {
      id: "domain-1",
      type: "domain",
      label: "Legal Research Domain",
      status: "active",
      x: 350,
      y: 40,
      width: 200,
      height: 70,
      description: "Contract analysis and compliance checking domain",
      metadata: {},
      folderPath: "/",
    },
    {
      id: "agent-1",
      type: "agent",
      label: "Contract Analyst",
      status: "active",
      x: 120,
      y: 170,
      width: 170,
      height: 85,
      description: "Analyzes legal contracts for risks and obligations",
      metadata: {},
      folderPath: "/agents/contract_analyst",
    },
    {
      id: "agent-2",
      type: "agent",
      label: "Compliance Checker",
      status: "idle",
      x: 360,
      y: 170,
      width: 170,
      height: 85,
      description: "Validates regulatory compliance",
      metadata: {},
      folderPath: "/agents/compliance_checker",
    },
    {
      id: "skill-1",
      type: "skill",
      label: "contract_analysis.py",
      status: "active",
      x: 120,
      y: 320,
      width: 170,
      height: 60,
      description: "Contract parsing and clause extraction",
      metadata: {},
      folderPath: "/skills/contract_analysis.py",
    },
    {
      id: "skill-2",
      type: "skill",
      label: "risk_scoring.py",
      status: "active",
      x: 360,
      y: 320,
      width: 170,
      height: 60,
      description: "Risk assessment algorithms",
      metadata: {},
      folderPath: "/skills/risk_scoring.py",
    },
    {
      id: "browser-1",
      type: "browser",
      label: "Contract Preview",
      status: "active",
      x: 600,
      y: 170,
      width: 170,
      height: 85,
      description: "Live HTML preview of contract UI",
      metadata: {},
      folderPath: "/ui/contract_preview",
    },
    {
      id: "wf-1",
      type: "workflow",
      label: "Full Contract Review",
      status: "active",
      x: 280,
      y: 440,
      width: 200,
      height: 70,
      description: "End-to-end contract review workflow",
      metadata: {},
      folderPath: "/workflows/full_contract_review",
    },
  ];
}

/** Generate mock canvas edges for testing. */
export function generateMockEdges(): CanvasEdge[] {
  return [
    { id: "e1", source: "domain-1", target: "agent-1", type: "group", metadata: {} },
    { id: "e2", source: "domain-1", target: "agent-2", type: "group", metadata: {} },
    { id: "e3", source: "domain-1", target: "browser-1", type: "group", metadata: {} },
    { id: "e4", source: "agent-1", target: "skill-1", type: "dependency", metadata: {} },
    { id: "e5", source: "agent-2", target: "skill-2", type: "dependency", metadata: {} },
    { id: "e6", source: "agent-1", target: "wf-1", type: "flow", label: "inputs", metadata: {} },
    { id: "e7", source: "agent-2", target: "wf-1", type: "flow", label: "validates", metadata: {} },
    { id: "e8", source: "skill-1", target: "wf-1", type: "data", metadata: {} },
  ];
}

/** Generate mock copilot suggestions for testing. */
export function generateMockSuggestions(): CopilotSuggestion[] {
  return [
    {
      suggestion_id: "s1",
      suggestion_type: "best_practice",
      title: "Add a Terminal node",
      description: "Consider adding a TUI node for command-line interaction with the domain.",
      confidence: 0.85,
      impact: "medium",
      target_node_ids: [],
      auto_applicable: false,
      details: {},
    },
    {
      suggestion_id: "s2",
      suggestion_type: "layout_optimization",
      title: "Reduce edge crossings",
      description: "Switching to clustered layout would improve readability.",
      confidence: 0.75,
      impact: "medium",
      target_node_ids: [],
      auto_applicable: true,
      details: {},
    },
    {
      suggestion_id: "s3",
      suggestion_type: "missing_connection",
      title: "Compliance Checker lacks skill access",
      description: "Connect the compliance checker to risk_scoring.py for better analysis.",
      confidence: 0.7,
      impact: "low",
      target_node_ids: ["agent-2"],
      auto_applicable: false,
      details: {},
    },
  ];
}

/** Generate mock simulation metrics for testing. */
export function generateMockSimulationMetrics(
  nodes: CanvasNode[],
): Record<string, Record<string, SimulationMetric>> {
  const metrics: Record<string, Record<string, SimulationMetric>> = {};
  for (const node of nodes) {
    if (node.type === "agent" || node.type === "skill") {
      metrics[node.id] = {
        exec_time: {
          metric_name: "exec_time",
          value: Math.random() * 3 + 0.5,
          unit: "ms",
          status: "normal",
          trend: "stable",
        },
        success_rate: {
          metric_name: "success_rate",
          value: Math.random() * 0.3 + 0.7,
          unit: "%",
          status: "normal",
          trend: "improving",
        },
      };
    }
  }
  return metrics;
}

/** Generate mock tape events for testing. */
export function generateMockTapeEvents(): TapeEventEntry[] {
  return [
    {
      event_id: "te1",
      event_type: "canvas.node_added",
      agent_id: "prime",
      source_node_id: "domain-1",
      target_node_id: "agent-1",
      payload: {},
      direction: "through",
    },
    {
      event_id: "te2",
      event_type: "canvas.edge_added",
      agent_id: "canvas-service",
      source_node_id: "agent-1",
      target_node_id: "skill-1",
      payload: {},
      direction: "through",
    },
  ];
}

/** Generate mock canvas versions for testing. */
export function generateMockVersions(): CanvasVersion[] {
  return [
    {
      version: 1,
      canvas_id: "mock-id",
      domain_id: "demo-domain",
      commit_message: "Initial canvas creation",
      author: "system",
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      version: 2,
      canvas_id: "mock-id",
      domain_id: "demo-domain",
      commit_message: "Added compliance checker agent",
      author: "prime",
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      version: 3,
      canvas_id: "mock-id",
      domain_id: "demo-domain",
      commit_message: "Applied smart auto-layout",
      author: "copilot",
      created_at: new Date().toISOString(),
    },
  ];
}
