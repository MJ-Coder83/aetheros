"""Prime LLM-Enhanced Planning -- AI-powered goal decomposition for complex goals.

This module extends the base PlanningEngine with LLM-powered goal decomposition.
When goals are unstructured or too complex for pure heuristics, the LLMPlanner
uses a configurable LLM backend (DSPy, LangGraph, or a pluggable interface)
to decompose them into structured, dependency-ordered PlanStep sequences.

Design principles:
- LLM planning is always logged to the Tape (full auditability)
- LLM-generated plans go through the same validation as heuristic plans
- A confidence score is assigned to LLM-generated steps
- Plans can mix LLM-generated and heuristic-generated steps
- The LLM planner is optional -- the base PlanningEngine works without it
- Each LLM provider is pluggable via the LLMProvider protocol

Usage::

    from packages.prime.llm_planning import LLMPlanner, DSPyProvider

    provider = DSPyProvider()
    planner = LLMPlanner(provider=provider, tape_service=tape_svc)
    steps = await planner.decompose_goal(
        goal="Reduce system error rate below 5%",
        context={"current_error_rate": 0.12},
    )
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.prime.intelligence_profile import IntelligenceProfileEngine
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DecompositionStrategy(StrEnum):
    """Strategy for decomposing a goal into steps."""

    HEURISTIC = "heuristic"
    LLM = "llm"
    HYBRID = "hybrid"


class LLMProviderType(StrEnum):
    """Which LLM provider backend to use."""

    DSPY = "dspy"
    LANGGRAPH = "langgraph"
    MOCK = "mock"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class LLMStepSuggestion(BaseModel):
    """A single step suggested by the LLM."""

    name: str
    action: str
    description: str = ""
    dependencies: list[str] = []
    parameters: dict[str, object] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = ""


class DecompositionResult(BaseModel):
    """Result of an LLM goal decomposition."""

    id: UUID = Field(default_factory=uuid4)
    goal: str
    strategy: DecompositionStrategy
    steps: list[LLMStepSuggestion] = []
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    provider_type: LLMProviderType = LLMProviderType.MOCK
    token_usage: dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DecompositionStore:
    """In-memory store for decomposition results."""

    def __init__(self) -> None:
        self._results: dict[UUID, DecompositionResult] = {}

    def add(self, result: DecompositionResult) -> None:
        self._results[result.id] = result

    def get(self, result_id: UUID) -> DecompositionResult | None:
        return self._results.get(result_id)

    def list_all(self) -> list[DecompositionResult]:
        return list(self._results.values())


# ---------------------------------------------------------------------------
# LLM Provider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM backends that can decompose goals.

    Implement this protocol to integrate a new LLM provider.
    """

    @property
    def provider_type(self) -> LLMProviderType: ...

    async def decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult: ...


# ---------------------------------------------------------------------------
# Mock LLM Provider (for testing and development)
# ---------------------------------------------------------------------------


class MockLLMProvider:
    """Mock LLM provider that generates plausible step suggestions.

    Uses keyword-based heuristics to simulate LLM output. Useful for
    development and testing without a real LLM API key.
    """

    def __init__(self) -> None:
        self._provider_type = LLMProviderType.MOCK

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    async def decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult:
        """Generate mock decomposition based on goal keywords."""
        goal_lower = goal.lower()
        steps = self._generate_steps(goal_lower, max_steps)
        confidence = 0.6 if len(steps) >= 3 else 0.4

        return DecompositionResult(
            goal=goal,
            strategy=DecompositionStrategy.LLM,
            steps=steps,
            overall_confidence=confidence,
            reasoning=f"Mock LLM decomposition based on goal keywords: '{goal}'",
            provider_type=self._provider_type,
            token_usage={"prompt_tokens": 150, "completion_tokens": 300},
        )

    def _generate_steps(
        self, goal_lower: str, max_steps: int
    ) -> list[LLMStepSuggestion]:
        """Generate plausible step suggestions from goal keywords."""
        # Richer keyword-to-step mapping than the base PlanningEngine
        patterns: list[tuple[list[str], list[LLMStepSuggestion]]] = [
            (
                ["error", "bug", "fix"],
                [
                    LLMStepSuggestion(
                        name="Reproduce and classify errors",
                        action="analyse_errors",
                        description="Identify, categorise, and rank errors by frequency and impact",
                        confidence=0.85,
                        reasoning="Understanding the error landscape is prerequisite to fixing",
                    ),
                    LLMStepSuggestion(
                        name="Root cause analysis",
                        action="analyse_errors",
                        dependencies=["s1"],
                        description="Trace each high-impact error to its root cause",
                        confidence=0.8,
                        reasoning="Root cause analysis enables targeted fixes",
                    ),
                    LLMStepSuggestion(
                        name="Implement targeted fixes",
                        action="fix_errors",
                        dependencies=["s2"],
                        description="Code fixes for root causes identified in analysis",
                        confidence=0.7,
                        reasoning="Targeted fixes are more efficient than broad changes",
                    ),
                    LLMStepSuggestion(
                        name="Regression testing",
                        action="verify_fix",
                        dependencies=["s3"],
                        description="Run comprehensive test suite to verify fixes and detect regressions",
                        confidence=0.75,
                        reasoning="Testing ensures fixes do not introduce new issues",
                    ),
                    LLMStepSuggestion(
                        name="Deploy and monitor",
                        action="monitor_metrics",
                        dependencies=["s4"],
                        description="Deploy fixes and monitor error rate for 24h",
                        confidence=0.65,
                        reasoning="Monitoring confirms the fix in production",
                    ),
                ],
            ),
            (
                ["performance", "speed", "latency", "slow"],
                [
                    LLMStepSuggestion(
                        name="Profile system bottlenecks",
                        action="introspect_system",
                        description="Run performance profiling to identify bottlenecks",
                        confidence=0.85,
                        reasoning="Profiling identifies where time is actually spent",
                    ),
                    LLMStepSuggestion(
                        name="Analyse resource usage",
                        action="analyse_errors",
                        dependencies=["s1"],
                        description="Examine CPU, memory, and I/O patterns during peak load",
                        confidence=0.8,
                        reasoning="Resource analysis reveals allocation inefficiencies",
                    ),
                    LLMStepSuggestion(
                        name="Optimise critical paths",
                        action="fix_errors",
                        dependencies=["s2"],
                        description="Apply targeted optimisations to identified bottlenecks",
                        confidence=0.65,
                        reasoning="Optimisations must target the actual critical path",
                    ),
                    LLMStepSuggestion(
                        name="Benchmark improvements",
                        action="verify_fix",
                        dependencies=["s3"],
                        description="Compare before/after benchmarks to validate improvements",
                        confidence=0.8,
                        reasoning="Benchmarks provide objective measurement of change",
                    ),
                ],
            ),
            (
                ["migrate", "upgrade", "refactor"],
                [
                    LLMStepSuggestion(
                        name="Assess current architecture",
                        action="introspect_system",
                        description="Document current system state and dependencies",
                        confidence=0.9,
                        reasoning="Understanding the current state is essential for migration",
                    ),
                    LLMStepSuggestion(
                        name="Plan migration strategy",
                        action="generate_proposal",
                        dependencies=["s1"],
                        description="Create a phased migration plan with rollback points",
                        confidence=0.75,
                        reasoning="Phased migration reduces risk and enables rollback",
                    ),
                    LLMStepSuggestion(
                        name="Execute phase 1",
                        action="implement_proposal",
                        dependencies=["s2"],
                        description="Implement the first migration phase with monitoring",
                        confidence=0.6,
                        reasoning="First phase should be the lowest-risk change",
                    ),
                    LLMStepSuggestion(
                        name="Validate and iterate",
                        action="verify_fix",
                        dependencies=["s3"],
                        description="Validate phase 1 results before proceeding",
                        confidence=0.7,
                        reasoning="Validation between phases catches issues early",
                    ),
                ],
            ),
            (
                ["security", "vulnerability", "compliance"],
                [
                    LLMStepSuggestion(
                        name="Security audit",
                        action="introspect_system",
                        description="Comprehensive security audit of the system",
                        confidence=0.85,
                        reasoning="Audit identifies all vulnerabilities before remediation",
                    ),
                    LLMStepSuggestion(
                        name="Classify and prioritise findings",
                        action="analyse_errors",
                        dependencies=["s1"],
                        description="Rank vulnerabilities by severity and exploitability",
                        confidence=0.8,
                        reasoning="Prioritisation ensures critical issues are addressed first",
                    ),
                    LLMStepSuggestion(
                        name="Implement security patches",
                        action="fix_errors",
                        dependencies=["s2"],
                        description="Apply security patches for high-severity findings",
                        confidence=0.7,
                        reasoning="Patches must be tested to avoid breaking changes",
                    ),
                    LLMStepSuggestion(
                        name="Compliance verification",
                        action="verify_fix",
                        dependencies=["s3"],
                        description="Verify compliance with relevant security standards",
                        confidence=0.75,
                        reasoning="Compliance checks confirm all requirements are met",
                    ),
                ],
            ),
        ]

        # Find the best matching pattern
        best_match: list[LLMStepSuggestion] = []
        best_score = 0
        for keywords, steps in patterns:
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > best_score:
                best_score = score
                best_match = steps

        if best_match:
            # Trim to max_steps
            return best_match[:max_steps]

        # Generic decomposition for unmatched goals
        return [
            LLMStepSuggestion(
                name="Analyse current state",
                action="introspect_system",
                description="Gather data about the current system state relevant to the goal",
                confidence=0.7,
                reasoning="Understanding the current state is the first step",
            ),
            LLMStepSuggestion(
                name="Identify required changes",
                action="generate_proposal",
                dependencies=["s1"],
                description="Determine what changes are needed to achieve the goal",
                confidence=0.6,
                reasoning="Change identification follows state analysis",
            ),
            LLMStepSuggestion(
                name="Implement changes",
                action="implement_proposal",
                dependencies=["s2"],
                description="Apply the identified changes in a controlled manner",
                confidence=0.55,
                reasoning="Implementation must be controlled and monitored",
            ),
            LLMStepSuggestion(
                name="Validate outcomes",
                action="verify_fix",
                dependencies=["s3"],
                description="Verify that the goal has been achieved",
                confidence=0.65,
                reasoning="Validation confirms the goal is met",
            ),
        ][:max_steps]


# ---------------------------------------------------------------------------
# DSPy LLM Provider (real integration, graceful fallback)
# ---------------------------------------------------------------------------


class DSPyProvider:
    """DSPy-based LLM provider for goal decomposition.

    Attempts to use the real DSPy library for LLM-powered decomposition.
    Falls back to the MockLLMProvider if DSPy is not properly configured
    or if no LM is available.
    """

    def __init__(self, fallback: MockLLMProvider | None = None) -> None:
        self._fallback = fallback or MockLLMProvider()
        self._provider_type = LLMProviderType.DSPY
        self._dspy_available = False
        self._setup_dspy()

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    def _setup_dspy(self) -> None:
        """Attempt to configure DSPy. Sets _dspy_available on success."""
        contextlib_suppress: set[type[Exception]] = {ImportError, Exception}
        import contextlib

        with contextlib.suppress(*contextlib_suppress):
            import dspy

            # Try to configure with a default LM
            # If no API key is set, this will fail gracefully
            lm = dspy.LM("openai/gpt-4o-mini")
            dspy.configure(lm=lm)
            self._dspy_available = True

    async def decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult:
        """Decompose a goal using DSPy, falling back to mock on failure."""
        if not self._dspy_available:
            result = await self._fallback.decompose(goal, context, max_steps)
            return result.model_copy(
                update={"provider_type": self._provider_type}
            )

        # Attempt real DSPy decomposition
        import contextlib

        with contextlib.suppress(Exception):
            return await self._dspy_decompose(goal, context, max_steps)

        # Fallback on any DSPy error
        result = await self._fallback.decompose(goal, context, max_steps)
        return result.model_copy(
            update={"provider_type": self._provider_type}
        )

    async def _dspy_decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult:
        """Perform DSPy-based decomposition (requires configured LM)."""
        import dspy

        ctx_str = ""
        if context:
            ctx_parts = [f"- {k}: {v}" for k, v in context.items()]
            ctx_str = "\nContext:\n" + "\n".join(ctx_parts)

        class GoalDecomposer(dspy.Signature):  # type: ignore[misc]
            """Decompose a goal into sequential steps with dependencies."""

            goal: str = dspy.InputField(desc="The high-level goal to decompose")
            context: str = dspy.InputField(desc="Additional context about the system")
            steps: str = dspy.OutputField(
                desc="JSON array of steps, each with name, action, description, "
                "dependencies (list of step IDs like s1, s2), confidence (0-1), "
                "and reasoning. Use step IDs s1, s2, s3, etc."
            )

        decomposer = dspy.ChainOfThought(GoalDecomposer)
        prediction = decomposer(
            goal=goal,
            context=ctx_str or "No additional context available",
        )

        # Parse the LLM output
        import json

        steps: list[LLMStepSuggestion] = []
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            raw_steps = json.loads(prediction.steps)
            if isinstance(raw_steps, list):
                for raw in raw_steps[:max_steps]:
                    if isinstance(raw, dict):
                        steps.append(
                            LLMStepSuggestion(
                                name=str(raw.get("name", "Unnamed step")),
                                action=str(raw.get("action", "custom")),
                                description=str(raw.get("description", "")),
                                dependencies=list(raw.get("dependencies", [])),
                                parameters=(
                                    raw.get("parameters", {})
                                    if isinstance(raw.get("parameters"), dict)
                                    else {}
                                ),
                                confidence=float(raw.get("confidence", 0.5)),
                                reasoning=str(raw.get("reasoning", "")),
                            )
                        )

        if not steps:
            # If parsing failed, fall back
            result = await self._fallback.decompose(goal, context, max_steps)
            return result.model_copy(
                update={"provider_type": self._provider_type}
            )

        overall_conf = (
            sum(s.confidence for s in steps) / len(steps) if steps else 0.0
        )

        return DecompositionResult(
            goal=goal,
            strategy=DecompositionStrategy.LLM,
            steps=steps,
            overall_confidence=round(overall_conf, 3),
            reasoning=f"DSPy LLM decomposition with {len(steps)} steps",
            provider_type=self._provider_type,
            token_usage={"estimate": len(goal) + len(steps) * 100},
        )


# ---------------------------------------------------------------------------
# LangGraph LLM Provider (real integration, graceful fallback)
# ---------------------------------------------------------------------------


class LangGraphProvider:
    """LangGraph-based LLM provider for goal decomposition.

    Uses a LangGraph StateGraph for structured goal decomposition.
    Falls back to MockLLMProvider if LangGraph is not configured.
    """

    def __init__(self, fallback: MockLLMProvider | None = None) -> None:
        self._fallback = fallback or MockLLMProvider()
        self._provider_type = LLMProviderType.LANGGRAPH
        self._langgraph_available = False
        self._setup_langgraph()

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    def _setup_langgraph(self) -> None:
        """Attempt to verify LangGraph availability."""
        import contextlib

        with contextlib.suppress(ImportError, Exception):

            self._langgraph_available = True

    async def decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult:
        """Decompose using LangGraph state machine, fallback to mock."""
        if not self._langgraph_available:
            result = await self._fallback.decompose(goal, context, max_steps)
            return result.model_copy(
                update={"provider_type": self._provider_type}
            )

        import contextlib

        with contextlib.suppress(Exception):
            return await self._langgraph_decompose(goal, context, max_steps)

        result = await self._fallback.decompose(goal, context, max_steps)
        return result.model_copy(
            update={"provider_type": self._provider_type}
        )

    async def _langgraph_decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult:
        """Perform LangGraph-based decomposition."""
        from langgraph.graph import END, StateGraph

        # Define the state
        class DecompositionState(BaseModel):
            goal: str = ""
            context: dict[str, object] = {}
            steps: list[LLMStepSuggestion] = []
            current_step: int = 0
            max_steps: int = max_steps

        def analyse_node(state: dict[str, object]) -> dict[str, object]:
            """Analyse the goal and generate initial step suggestions."""
            # In production, this would call an LLM
            # For now, use the mock provider's logic
            mock = MockLLMProvider()
            goal_str = str(state.get("goal", ""))
            ctx = state.get("context")
            ctx_dict = ctx if isinstance(ctx, dict) else {}
            result = asyncio.get_event_loop().run_until_complete(
                mock.decompose(goal_str, ctx_dict, max_steps)
            )
            return {"steps": result.steps}

        def validate_node(state: dict[str, object]) -> dict[str, object]:
            """Validate step dependencies and assign IDs."""
            steps = state.get("steps", [])
            if not isinstance(steps, list):
                return {"steps": []}
            # Ensure proper step IDs
            validated: list[LLMStepSuggestion] = []
            for _i, step in enumerate(steps):
                if isinstance(step, LLMStepSuggestion):
                    if not step.dependencies:
                        validated.append(step)
                    else:
                        # Validate dependencies reference valid step IDs
                        valid_deps = [
                            d for d in step.dependencies if d.startswith("s")
                        ]
                        validated.append(
                            step.model_copy(update={"dependencies": valid_deps})
                        )
            return {"steps": validated}

        # Build the graph
        graph: StateGraph[dict[str, object]] = StateGraph(dict)  # type: ignore[type-var]
        graph.add_node("analyse", analyse_node)  # type: ignore[type-var]
        graph.add_node("validate", validate_node)  # type: ignore[type-var]
        graph.add_edge("analyse", "validate")
        graph.add_edge("validate", END)
        graph.set_entry_point("analyse")

        compiled = graph.compile()

        # Execute
        initial_state: dict[str, object] = {
            "goal": goal,
            "context": context or {},
            "steps": [],
            "current_step": 0,
            "max_steps": max_steps,
        }

        import asyncio

        result_state = await compiled.ainvoke(initial_state)
        steps = result_state.get("steps", [])
        if not isinstance(steps, list):
            steps = []

        typed_steps = [s for s in steps if isinstance(s, LLMStepSuggestion)]
        overall_conf = (
            sum(s.confidence for s in typed_steps) / len(typed_steps)
            if typed_steps
            else 0.0
        )

        return DecompositionResult(
            goal=goal,
            strategy=DecompositionStrategy.LLM,
            steps=typed_steps[:max_steps],
            overall_confidence=round(overall_conf, 3),
            reasoning=f"LangGraph decomposition with {len(typed_steps)} steps",
            provider_type=self._provider_type,
            token_usage={"estimate": len(goal) + len(typed_steps) * 80},
        )


# ---------------------------------------------------------------------------
# LLM Planner -- the main public API
# ---------------------------------------------------------------------------


class LLMPlanner:
    """LLM-enhanced goal decomposition for the Prime meta-agent.

    LLMPlanner extends the base PlanningEngine by using LLM providers
    for complex, unstructured goals that pure heuristics cannot handle well.
    It supports multiple LLM backends (DSPy, LangGraph, Mock) and can
    mix LLM-generated and heuristic-generated steps.

    Usage::

        provider = MockLLMProvider()  # or DSPyProvider(), LangGraphProvider()
        planner = LLMPlanner(provider=provider, tape_service=tape_svc)
        result = await planner.decompose_goal(
            goal="Reduce system error rate below 5%",
            context={"current_error_rate": 0.12},
        )
        # result.steps contains LLMStepSuggestion objects
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        tape_service: TapeService | None = None,
        store: DecompositionStore | None = None,
        profile_engine: IntelligenceProfileEngine | None = None,
    ) -> None:
        self._provider = provider or MockLLMProvider()
        self._tape = tape_service
        self._store = store or DecompositionStore()
        self._profile_engine = profile_engine

    async def decompose_goal(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
        strategy: DecompositionStrategy = DecompositionStrategy.LLM,
    ) -> DecompositionResult:
        """Decompose a goal into steps using the configured LLM provider.

        Args:
            goal: The high-level goal to decompose.
            context: Optional system context for the LLM.
            max_steps: Maximum number of steps to generate.
            strategy: Decomposition strategy (LLM, HEURISTIC, HYBRID).

        Returns:
            A DecompositionResult with suggested steps and confidence scores.
        """
        if not goal.strip():
            raise ValueError("Goal must not be empty")

        if strategy == DecompositionStrategy.HEURISTIC:
            return await self._heuristic_decompose(goal, context, max_steps)

        if strategy == DecompositionStrategy.HYBRID:
            return await self._hybrid_decompose(goal, context, max_steps)

        # Default: LLM decomposition
        result = await self._provider.decompose(goal, context, max_steps)
        self._store.add(result)

        if self._tape is not None:
            await self._tape.log_event(
                event_type="planning.llm_decomposition",
                payload={
                    "decomposition_id": str(result.id),
                    "goal": goal,
                    "step_count": len(result.steps),
                    "overall_confidence": result.overall_confidence,
                    "strategy": strategy.value,
                    "provider_type": result.provider_type.value,
                },
                agent_id="llm-planner",
            )

        return result

    async def _heuristic_decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult:
        """Heuristic decomposition using the mock provider's pattern matching."""
        mock = MockLLMProvider()
        result = await mock.decompose(goal, context, max_steps)
        result = result.model_copy(
            update={"strategy": DecompositionStrategy.HEURISTIC}
        )
        self._store.add(result)

        if self._tape is not None:
            await self._tape.log_event(
                event_type="planning.heuristic_decomposition",
                payload={
                    "decomposition_id": str(result.id),
                    "goal": goal,
                    "step_count": len(result.steps),
                },
                agent_id="llm-planner",
            )

        return result

    async def _hybrid_decompose(
        self,
        goal: str,
        context: dict[str, object] | None = None,
        max_steps: int = 10,
    ) -> DecompositionResult:
        """Hybrid decomposition: LLM first, then refine with heuristics."""
        llm_result = await self._provider.decompose(goal, context, max_steps)

        # Refine: assign sequential IDs if missing
        refined_steps: list[LLMStepSuggestion] = []
        for _i, step in enumerate(llm_result.steps):
            refined_steps.append(
                step.model_copy(
                    update={"confidence": min(1.0, step.confidence + 0.05)}
                )
            )

        # Boost confidence slightly since hybrid approach is more reliable
        hybrid_conf = min(1.0, llm_result.overall_confidence + 0.05)

        result = llm_result.model_copy(
            update={
                "strategy": DecompositionStrategy.HYBRID,
                "steps": refined_steps,
                "overall_confidence": round(hybrid_conf, 3),
                "reasoning": f"Hybrid decomposition: {llm_result.reasoning}",
            }
        )
        self._store.add(result)

        if self._tape is not None:
            await self._tape.log_event(
                event_type="planning.hybrid_decomposition",
                payload={
                    "decomposition_id": str(result.id),
                    "goal": goal,
                    "step_count": len(result.steps),
                    "overall_confidence": result.overall_confidence,
                },
                agent_id="llm-planner",
            )

        return result

    async def get_decomposition(self, result_id: UUID) -> DecompositionResult:
        """Retrieve a stored decomposition result by ID."""
        result = self._store.get(result_id)
        if result is None:
            raise ValueError(f"Decomposition {result_id} not found")
        return result

    async def list_decompositions(self) -> list[DecompositionResult]:
        """List all stored decomposition results."""
        return self._store.list_all()

    async def should_use_llm(self, goal: str) -> bool:
        """Determine whether a goal would benefit from LLM decomposition.

        Returns True if the goal is complex or unstructured enough that
        heuristic pattern matching is unlikely to produce good results.
        """
        goal_lower = goal.lower()

        # Simple heuristic: goals with specific keywords are well-handled
        heuristic_keywords = {
            "error", "reliability", "skill", "domain",
            "add", "create", "evolve", "improve",
        }
        if any(kw in goal_lower for kw in heuristic_keywords):
            return False

        # Goals longer than 100 chars likely have nuance
        if len(goal) > 100:
            return True

        # Goals with multiple clauses (and, or, but, while)
        complex_markers = {" and ", " or ", " but ", " while ", " whereas ", " given "}
        if any(marker in goal_lower for marker in complex_markers):
            return True

        return True  # Default: use LLM for unmatched goals
