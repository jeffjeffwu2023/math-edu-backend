# routes/answers.py
from fastapi import APIRouter, HTTPException
from models.answer import Answer
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter()

@router.get("/")
async def get_answers(student_id: str = None):
    try:
        query = {"studentId": student_id} if student_id else {}
        answers = []
        async for answer in db.answers.find(query):
            answer.pop("_id", None)
            answers.append(answer)
        return answers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def add_answer(answer: Answer):
    try:
        answer_dict = answer.dict()
        result = await db.answers.insert_one(answer_dict)
        return {"message": "Answer added", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))