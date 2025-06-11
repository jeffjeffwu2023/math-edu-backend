# routes/answers.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from .auth import get_current_user
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/answers", tags=["answers"])

class Answer(BaseModel):
    id: str | None = None
    studentId: str
    questionId: str
    answer: str
    isCorrect: bool
    createdAt: str

@router.post("/")
async def add_answer(answer: Answer, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student" or current_user["id"] != answer.studentId:
        raise HTTPException(403, "Only students can submit their own answers")
    # Validate questionId
    question = await db.questions.find_one({"id": answer.questionId})
    if not question:
        raise HTTPException(404, "Question not found")
    answer_dict = answer.dict(exclude={"id"})
    answer_dict["id"] = str(ObjectId())
    answer_dict["createdAt"] = datetime.utcnow()
    await db.answers.insert_one(answer_dict)
    
    # Update user performance
    user = await db.users.find_one({"id": answer.studentId})
    if not user:
        raise HTTPException(404, "Student not found")
    
    performance_update = {
        "$inc": {
            "performanceData.totalAttempts": 1
        }
    }
    if answer.isCorrect:
        performance_update["$inc"]["performanceData.totalCorrect"] = 1
    await db.users.update_one({"id": answer.studentId}, performance_update)
    
    return {"id": answer_dict["id"], "message": "Answer submitted"}

@router.get("/")
async def get_answers(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "tutor"] and current_user["id"] != student_id:
        raise HTTPException(403, "Unauthorized access")
    answers = await db.answers.find({"studentId": student_id}).to_list(None)
    return [
        {
            "id": answer["id"],
            "studentId": answer["studentId"],
            "questionId": answer["questionId"],
            "answer": answer["answer"],
            "category": answer["category"]  if "category" in answer else "",
            "difficulty": answer["difficulty"] if "difficulty" in answer else "",
            "isCorrect": answer["isCorrect"] ,
            "createdAt": answer["createdAt"]
        }
        for answer in answers
    ]