# routes/questions.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from typing import List
from datetime import datetime
from models.question import Question
import uuid

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/questions", tags=["questions"])

class QuestionResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str | None
    difficulty: str
    knowledgePoints: List[dict]
    createdAt: str
    updatedAt: str
    isActive: bool

@router.post("/", response_model=QuestionResponse)
async def add_question(question: Question):
    # Validate knowledge point IDs
    valid_points = await db.knowledge_points.find(
        {"id": {"$in": question.knowledgePoints}, "isActive": True}
    ).to_list(None)
    if len(valid_points) != len(question.knowledgePoints):
        raise HTTPException(400, "Some knowledge point IDs are invalid or inactive")

    question_dict = question.dict(exclude={"id"})
    question_dict["id"] = str(uuid.uuid4())
    question_dict["knowledgePoints"] = question.knowledgePoints  # Store UUIDs
    question_dict["createdAt"] = datetime.utcnow().isoformat()
    question_dict["updatedAt"] = datetime.utcnow().isoformat()
    question_dict["isActive"] = True

    await db.questions.insert_one(question_dict)
    question_dict["knowledgePoints"] = [
        {
            "id": p["id"],
            "grade": p["grade"],
            "strand": p["strand"],
            "topic": p["topic"],
            "skill": p["skill"],
            "subKnowledgePoint": p["subKnowledgePoint"]
        }
        for p in valid_points
    ]
    return question_dict

@router.get("/", response_model=List[QuestionResponse])
async def get_questions():
    questions = await db.questions.find({"isActive": True}).to_list(None)
    for question in questions:
        question["knowledgePoints"] = await db.knowledge_points.find(
            {"id": {"$in": question["knowledgePoints"]}, "isActive": True}
        ).to_list(None)
        question["knowledgePoints"] = [
            {
                "id": p["id"],
                "grade": p["grade"],
                "strand": p["strand"],
                "topic": p["topic"],
                "skill": p["skill"],
                "subKnowledgePoint": p["subKnowledgePoint"]
            }
            for p in question["knowledgePoints"]
        ]
    return questions