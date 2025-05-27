# routes/answers.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from .auth import get_current_user
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/answers", tags=["answers"])

class Answer(BaseModel):
    studentId: str
    questionIndex: int
    answer: str
    isCorrect: bool
    timestamp: str

@router.post("/")
async def add_answer(answer: Answer, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student" or current_user["id"] != answer.studentId:
        raise HTTPException(403, "Only students can submit their own answers")
    answer_dict = answer.dict()
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
    
    return {"message": "Answer submitted"}

@router.get("/")
async def get_answers(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "tutor"] and current_user["id"] != student_id:
        raise HTTPException(403, "Unauthorized access")
    answers = await db.answers.find({"studentId": student_id}).to_list(None)
    return answers