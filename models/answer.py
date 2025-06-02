# models/answer.py
from pydantic import BaseModel
from datetime import datetime

class Answer(BaseModel):
    questionIndex: int
    studentId: str
    answer: str
    difficulty: str = "easy"  # Default difficulty
    category: str = "general"  # Default category
    isCorrect: bool = False
    timeTaken: int = 0  # In seconds
    createdAt: datetime = datetime.utcnow()