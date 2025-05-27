# routes/questions.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from typing import List
from datetime import datetime

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/questions", tags=["questions"])

class Question(BaseModel):
    title: str
    content: str
    category: str
    difficulty: str
    knowledgePoints: List[str]

class QuestionResponse(BaseModel):
    index: int
    title: str
    content: str
    category: str
    difficulty: str
    knowledgePoints: List[dict]
    createdAt: str
    updatedAt: str
    isActive: bool
    _id: str

@router.post("/", response_model=QuestionResponse)
async def add_question(question: Question):
    # Validate knowledge point IDs
    try:
        knowledge_point_ids = [ObjectId(kp_id) for kp_id in question.knowledgePoints]
    except:
        raise HTTPException(400, "Invalid knowledge point IDs")
    
    valid_points = await db.knowledge_points.find(
        {"_id": {"$in": knowledge_point_ids}, "isActive": True}
    ).to_list(None)
    if len(valid_points) != len(knowledge_point_ids):
        raise HTTPException(400, "Some knowledge point IDs are invalid or inactive")

    question_dict = question.dict()
    question_dict["index"] = await db.questions.count_documents({}) + 1
    question_dict["knowledgePoints"] = knowledge_point_ids
    question_dict["createdAt"] = datetime.utcnow().isoformat()
    question_dict["updatedAt"] = datetime.utcnow().isoformat()
    question_dict["isActive"] = True

    result = await db.questions.insert_one(question_dict)
    question_dict["_id"] = str(result.inserted_id)
    question_dict["knowledgePoints"] = [
        {"_id": str(p["_id"]), "grade": p["grade"], "strand": p["strand"], "topic": p["topic"], "skill": p["skill"], "subKnowledgePoint": p["subKnowledgePoint"]}
        for p in valid_points
    ]
    return question_dict

@router.get("/", response_model=List[QuestionResponse])
async def get_questions():
    questions = await db.questions.find({"isActive": True}).to_list(None)
    for question in questions:
        question["_id"] = str(question["_id"])
        question["knowledgePoints"] = await db.knowledge_points.find(
            {"_id": {"$in": question["knowledgePoints"]}, "isActive": True}
        ).to_list(None)
        question["knowledgePoints"] = [
            {"_id": str(p["_id"]), "grade": p["grade"], "strand": p["strand"], "topic": p["topic"], "skill": p["skill"], "subKnowledgePoint": p["subKnowledgePoint"]}
            for p in question["knowledgePoints"]
        ]
    return questions