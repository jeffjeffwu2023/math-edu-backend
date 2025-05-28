# models/knowledge_point.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class KnowledgePoint(BaseModel):
    id: Optional[str] = None  # MongoDB ObjectId as string
    grade: str  # e.g., "Grade 8"
    strand: str  # e.g., "Number"
    topic: str  # e.g., "Operations with Rational Numbers"
    skill: str  # e.g., "Add and subtract rational numbers"
    subKnowledgePoint: str  # e.g., "Add fractions with unlike denominators"
    version: str = "2025.01"
    isActive: bool = True
    createdAt: datetime = datetime.utcnow()
    updatedAt: datetime = datetime.utcnow()

class KnowledgePointResponse(KnowledgePoint):
    id: str