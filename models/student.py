# models/student.py
from pydantic import BaseModel
from datetime import datetime

class Student(BaseModel):
    id: str
    name: str
    email: str
    language: str = "en"  # For multilingual support (e.g., "en", "zh-CN")
    createdAt: datetime = datetime.utcnow()