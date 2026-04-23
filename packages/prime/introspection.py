"""Prime Introspection — Deep system self-awareness.

PrimeIntrospector allows the Prime meta-agent to query the full state of the
InkosAI system: Tape history, AetherGit commits, registered agents, skills,
and domains. Every introspection call is itself logged to the Tape, creating
a recursive self-awareness loop.

Design principles:
- Every introspection call is logged to the Tape (Prime observes itself)
- All queries go through the TapeService so the audit trail is complete
- SystemSnapshot is a Pydantic model — serialisable, versionable, queryable
"""

import platform
import sys
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from packages.tape.models import TapeEntry
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class AgentDescriptor(BaseModel):
    """Metadata about a registered agent in the system."""

    agent_id: str
    name: str
    capabilities: list[str] = []
    status: str = "unknown"
    last_seen: datetime | None = None


class SkillDescriptor(BaseModel):
    """Metadata about a registered skill."""

    skill_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""


class DomainDescriptor(BaseModel):
    """Metadata about a registered domain (problem space)."""

    domain_id: str
    name: str
    description: str = ""
    agent_count: int = 0


class SystemSnapshot(BaseModel):
    """Complete point-in-time snapshot of the InkosAI system state.

    Prime uses this to understand what the system looks like right now —
    its agents, skills, domains, recent Tape activity, and infrastructure.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    system_info: dict[str, str] = {}
    tape_stats: dict[str, int] = {}
    recent_tape_entries: list[TapeEntry] = []
    agents: list[AgentDescriptor] = []
    skills: list[SkillDescriptor] = []
    domains: list[DomainDescriptor] = []
    active_worktrees: list[str] = []
    health_status: str = "unknown"


# ---------------------------------------------------------------------------
# Registry (in-memory for now; will be backed by Postgres later)
# ---------------------------------------------------------------------------


class AgentRegistry:
    """In-memory registry of known agents.

    In production this will be backed by PostgreSQL. For now, agents are
    registered at startup or via the API.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentDescriptor] = {}

    def register(self, agent: AgentDescriptor) -> None:
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def list_agents(self) -> list[AgentDescriptor]:
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> AgentDescriptor | None:
        return self._agents.get(agent_id)


class SkillRegistry:
    """In-memory registry of known skills."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDescriptor] = {}

    def register(self, skill: SkillDescriptor) -> None:
        self._skills[skill.skill_id] = skill

    def unregister(self, skill_id: str) -> None:
        self._skills.pop(skill_id, None)

    def list_skills(self) -> list[SkillDescriptor]:
        return list(self._skills.values())


class DomainRegistry:
    """In-memory registry of known domains."""

    def __init__(self) -> None:
        self._domains: dict[str, DomainDescriptor] = {}

    def register(self, domain: DomainDescriptor) -> None:
        self._domains[domain.domain_id] = domain

    def unregister(self, domain_id: str) -> None:
        self._domains.pop(domain_id, None)

    def list_domains(self) -> list[DomainDescriptor]:
        return list(self._domains.values())


# ---------------------------------------------------------------------------
# PrimeIntrospector
# ---------------------------------------------------------------------------


class PrimeIntrospector:
    """Deep system introspection engine for the Prime meta-agent.

    PrimeIntrospector gives Prime the ability to observe and understand the
    entire system state. Every introspection call is logged to the Tape so
    that Prime's self-observation is itself part of the audit trail.

    Usage::

        tape_svc = TapeService(InMemoryTapeRepository())
        introspector = PrimeIntrospector(tape_service=tape_svc)
        snapshot = await introspector.snapshot()
        # snapshot contains the full system state
    """

    def __init__(
        self,
        tape_service: TapeService,
        agent_registry: AgentRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        domain_registry: DomainRegistry | None = None,
    ) -> None:
        self._tape = tape_service
        self._agents = agent_registry or AgentRegistry()
        self._skills = skill_registry or SkillRegistry()
        self._domains = domain_registry or DomainRegistry()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def snapshot(self) -> SystemSnapshot:
        """Capture a full point-in-time snapshot of the system.

        This is Prime's primary self-awareness method. It queries every
        subsystem and returns a unified view.
        """
        recent_entries = await self._tape.get_recent_entries(limit=20)
        tape_stats = await self._compute_tape_stats()

        snapshot = SystemSnapshot(
            system_info=self._collect_system_info(),
            tape_stats=tape_stats,
            recent_tape_entries=recent_entries,
            agents=self._agents.list_agents(),
            skills=self._skills.list_skills(),
            domains=self._domains.list_domains(),
            active_worktrees=self._list_worktrees(),
            health_status="healthy",
        )

        # Log the introspection event to the Tape
        await self._tape.log_event(
            event_type="prime.introspection",
            payload={"snapshot_id": str(snapshot.timestamp.isoformat())},
            agent_id="prime",
            metadata={"entry_count": len(recent_entries)},
        )

        return snapshot

    async def query_tape(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[TapeEntry]:
        """Query the Tape with optional filters.

        Prime can search for specific event types, agent actions, or
        just browse the most recent activity.
        """
        entries = await self._tape.get_entries(
            event_type=event_type,
            agent_id=agent_id,
            limit=limit,
        )
        await self._tape.log_event(
            event_type="prime.tape_query",
            payload={
                "filters": {
                    "event_type": event_type,
                    "agent_id": agent_id,
                    "limit": limit,
                }
            },
            agent_id="prime",
        )
        return entries

    async def get_agent_status(self, agent_id: str) -> AgentDescriptor | None:
        """Look up a specific agent's status."""
        agent = self._agents.get_agent(agent_id)
        await self._tape.log_event(
            event_type="prime.agent_lookup",
            payload={"target_agent_id": agent_id, "found": agent is not None},
            agent_id="prime",
        )
        return agent

    async def list_skills(self) -> list[SkillDescriptor]:
        """List all registered skills in the system."""
        skills = self._skills.list_skills()
        await self._tape.log_event(
            event_type="prime.skill_list",
            payload={"skill_count": len(skills)},
            agent_id="prime",
        )
        return skills

    async def list_domains(self) -> list[DomainDescriptor]:
        """List all registered domains in the system."""
        domains = self._domains.list_domains()
        await self._tape.log_event(
            event_type="prime.domain_list",
            payload={"domain_count": len(domains)},
            agent_id="prime",
        )
        return domains

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _compute_tape_stats(self) -> dict[str, int]:
        """Compute summary statistics from the Tape."""
        all_entries = await self._tape.get_recent_entries(limit=1000)
        event_type_counts: dict[str, int] = {}
        agent_counts: dict[str, int] = {}
        for entry in all_entries:
            event_type_counts[entry.event_type] = event_type_counts.get(entry.event_type, 0) + 1
            if entry.agent_id is not None:
                agent_counts[entry.agent_id] = agent_counts.get(entry.agent_id, 0) + 1
        return {
            "total_entries": len(all_entries),
            "unique_event_types": len(event_type_counts),
            "unique_agents": len(agent_counts),
        }

    @staticmethod
    def _collect_system_info() -> dict[str, str]:
        """Collect runtime environment information."""
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "platform_node": platform.node(),
            "python_implementation": platform.python_implementation(),
        }

    @staticmethod
    def _list_worktrees() -> list[str]:
        """List active git worktrees (best-effort, non-fatal on failure)."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return []
            worktrees: list[str] = []
            for line in result.stdout.strip().splitlines():
                if line.startswith("worktree "):
                    worktrees.append(line.removeprefix("worktree "))
            return worktrees
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return []
