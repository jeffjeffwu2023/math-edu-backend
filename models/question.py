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
    correctAnswer: Optional[str] = None  # Added field for correct answer
    passValidation: bool = False  # Added field for validation status
    createdAt: datetime = datetime.utcnow()    