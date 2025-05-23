# models/question.py
from pydantic import BaseModel
from datetime import datetime

class Question(BaseModel):
    title: str
    content: str
    difficulty: str = "easy"
    category: str
    createdAt: datetime = datetime.utcnow()