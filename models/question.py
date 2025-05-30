# models/question.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Question(BaseModel):
    id: Optional[str] = None  # UUID as string
    title: str
    content: str
    difficulty: str = "easy"
    category: Optional[str] = None
    knowledgePoints: List[str] = []  # List of knowledge point UUID strings
    createdAt: datetime = datetime.utcnow()