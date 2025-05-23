# models/answer.py
from pydantic import BaseModel
from datetime import datetime

class Answer(BaseModel):
    questionIndex: int
    studentId: str
    answer: str
    isCorrect: bool = False
    timeTaken: int = 0  # In seconds
    createdAt: datetime = datetime.utcnow()