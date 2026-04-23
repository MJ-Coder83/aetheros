from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Dict, Optional


class AetherCommit(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    parent_ids: List[UUID] = []
    author: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: str
    commit_type: str
    scope: str
    performance_metrics: Dict[str, float] = {}
    confidence_score: float = 0.0
    tape_references: List[UUID] = []
    tree_id: Optional[UUID] = None
    proposed_by: Optional[str] = None
    evolution_approved: bool = False
