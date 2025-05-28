# models/question.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Question(BaseModel):
    title: str
    content: str
    difficulty: str = "easy"
    category: Optional[str] = None  # Optional, as categories are removed
    knowledgePoints: List[str] = []  # List of knowledge point ObjectId strings
    createdAt: datetime = datetime.utcnow()