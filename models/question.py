# models/question.py
from pydantic import BaseModel
from datetime import datetime

class Question(BaseModel):
    title: str
    content: str
    difficulty: str = "easy"
    category: Optional[str] = None  # Optional if using knowledge points
    knowledge_points: List[str] = []  # List of knowledge point IDs
    created_at: datetime = datetime.utcnow()