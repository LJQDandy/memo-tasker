from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Task:
    id: Optional[int] = None
    title: str = ""
    due_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    status: str = "pending"  # pending/completed
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
