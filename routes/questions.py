# routes/questions.py
from fastapi import APIRouter, HTTPException
from models.question import Question
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter()

@router.get("/")
async def get_questions():
    try:
        questions = []
        async for question in db.questions.find():
            question.pop("_id", None)
            questions.append(question)
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def add_question(question: Question):
    try:
        question_dict = question.dict()
        result = await db.questions.insert_one(question_dict)
        return {"message": "Question added", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))