# models/course.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Course(BaseModel):
    id: Optional[str] = None  # UUID as string
    name: str
    description: str
    grade: str
    knowledgePointIds: List[str] = []  # UUIDs from knowledge_points
    questionIds: List[str] = []  # UUIDs from questions
    isActive: bool = True
    createdAt: datetime = datetime.utcnow()
    updatedAt: datetime = datetime.utcnow()

class CourseResponse(Course):
    id: str