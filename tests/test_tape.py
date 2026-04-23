"""Unit tests for the Tape service — using the in-memory repository.

Run with:  pytest tests/test_tape.py -v
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from packages.tape.repository import InMemoryTapeRepository
from packages.tape.schemas import TapeEntryCreate, TapeEntryFilter
from packages.tape.service import TapeEntryNotFoundError, TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo() -> InMemoryTapeRepository:
    return InMemoryTapeRepository()


@pytest.fixture()
def svc(repo: InMemoryTapeRepository) -> TapeService:
    return TapeService(repo)


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_event_returns_entry(svc: TapeService) -> None:
    entry = await svc.log_event(
        event_type="agent.invoke",
        payload={"tool": "search"},
        agent_id="agent-001",
    )
    assert isinstance(entry.id, UUID)
    assert entry.event_type == "agent.invoke"
    assert entry.agent_id == "agent-001"
    assert entry.payload == {"tool": "search"}
    assert isinstance(entry.timestamp, datetime)


@pytest.mark.asyncio
async def test_log_event_with_metadata_and_commit(svc: TapeService) -> None:
    commit_id = UUID("11111111-1111-1111-1111-111111111111")
    entry = await svc.log_event(
        event_type="commit.create",
        payload={"scope": "core"},
        metadata={"source": "prime"},
        commit_id=commit_id,
    )
    assert entry.metadata == {"source": "prime"}
    assert entry.commit_id == commit_id


@pytest.mark.asyncio
async def test_log_event_defaults(svc: TapeService) -> None:
    entry = await svc.log_event(
        event_type="system.start",
        payload={},
    )
    assert entry.agent_id is None
    assert entry.commit_id is None
    assert entry.metadata == {}


# ---------------------------------------------------------------------------
# get_entry_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entry_by_id_found(svc: TapeService) -> None:
    created = await svc.log_event(event_type="test", payload={"v": 1})
    fetched = await svc.get_entry_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.event_type == "test"


@pytest.mark.asyncio
async def test_get_entry_by_id_not_found(svc: TapeService) -> None:
    with pytest.raises(TapeEntryNotFoundError):
        await svc.get_entry_by_id(UUID("00000000-0000-0000-0000-000000000000"))


# ---------------------------------------------------------------------------
# get_entries (filters)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entries_no_filters(svc: TapeService) -> None:
    await svc.log_event(event_type="a", payload={})
    await svc.log_event(event_type="b", payload={})
    results = await svc.get_entries()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_entries_filter_by_event_type(svc: TapeService) -> None:
    await svc.log_event(event_type="agent.invoke", payload={})
    await svc.log_event(event_type="commit.create", payload={})
    await svc.log_event(event_type="agent.invoke", payload={})
    results = await svc.get_entries(event_type="agent.invoke")
    assert len(results) == 2
    assert all(e.event_type == "agent.invoke" for e in results)


@pytest.mark.asyncio
async def test_get_entries_filter_by_agent_id(svc: TapeService) -> None:
    await svc.log_event(event_type="task", payload={}, agent_id="agent-a")
    await svc.log_event(event_type="task", payload={}, agent_id="agent-b")
    results = await svc.get_entries(agent_id="agent-a")
    assert len(results) == 1
    assert results[0].agent_id == "agent-a"


@pytest.mark.asyncio
async def test_get_entries_filter_by_commit_id(svc: TapeService) -> None:
    cid = UUID("22222222-2222-2222-2222-222222222222")
    await svc.log_event(event_type="commit.create", payload={}, commit_id=cid)
    await svc.log_event(event_type="commit.create", payload={})
    results = await svc.get_entries(commit_id=cid)
    assert len(results) == 1
    assert results[0].commit_id == cid


@pytest.mark.asyncio
async def test_get_entries_filter_by_time_range(svc: TapeService) -> None:
    now = datetime.now(UTC)
    early = (now - timedelta(hours=2)).isoformat()
    late = (now + timedelta(hours=1)).isoformat()

    await svc.log_event(event_type="old", payload={})
    await svc.log_event(event_type="recent", payload={})

    # Both should fall within the wide range
    results = await svc.get_entries(from_time=early, to_time=late)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_entries_limit(svc: TapeService) -> None:
    for i in range(10):
        await svc.log_event(event_type=f"evt-{i}", payload={})
    results = await svc.get_entries(limit=3)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# get_recent_entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recent_entries(svc: TapeService) -> None:
    await svc.log_event(event_type="first", payload={})
    second = await svc.log_event(event_type="second", payload={})
    third = await svc.log_event(event_type="third", payload={})

    recent = await svc.get_recent_entries(limit=2)
    assert len(recent) == 2
    # newest first
    assert recent[0].id == third.id
    assert recent[1].id == second.id


@pytest.mark.asyncio
async def test_get_recent_entries_default_limit(svc: TapeService) -> None:
    for i in range(60):
        await svc.log_event(event_type=f"evt-{i}", payload={})
    results = await svc.get_recent_entries()
    assert len(results) == 50  # default limit


# ---------------------------------------------------------------------------
# Repository-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_in_memory_repo_log_and_get(repo: InMemoryTapeRepository) -> None:
    create = TapeEntryCreate(event_type="test", payload={"k": "v"})
    entry = await repo.log_event(create)
    assert isinstance(entry.id, UUID)

    fetched = await repo.get_entry_by_id(entry.id)
    assert fetched is not None
    assert fetched.payload == {"k": "v"}


@pytest.mark.asyncio
async def test_in_memory_repo_get_entries_with_filter(
    repo: InMemoryTapeRepository,
) -> None:
    await repo.log_event(TapeEntryCreate(event_type="alpha", payload={}, agent_id="a1"))
    await repo.log_event(TapeEntryCreate(event_type="beta", payload={}, agent_id="a2"))
    await repo.log_event(TapeEntryCreate(event_type="alpha", payload={}, agent_id="a1"))

    filters = TapeEntryFilter(event_type="alpha", agent_id="a1")
    results = await repo.get_entries(filters)
    assert len(results) == 2
