# models/assignment.py
from pydantic import BaseModel
from datetime import datetime
from typing import List

class Assignment(BaseModel):
    id: int
    questionIndices: List[int]
    studentId: str
    submitted: bool = False
    createdAt: datetime = datetime.utcnow()