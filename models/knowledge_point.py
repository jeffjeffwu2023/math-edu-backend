# models/knowledge_point.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class KnowledgePoint(BaseModel):
    id: Optional[str] = None  # UUID as string
    grade: str
    strand: str
    topic: str
    skill: str
    subKnowledgePoint: str
    version: str = "2025.01"
    isActive: bool = True
    createdAt: datetime = datetime.utcnow()
    updatedAt: datetime = datetime.utcnow()

class KnowledgePointResponse(KnowledgePoint):
    id: str