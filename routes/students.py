# routes/students.py
from fastapi import APIRouter, HTTPException, Depends
from models.student import Student
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter()

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@router.get("/", dependencies=[Depends(get_current_user)])
async def get_students():
    try:
        students = []
        async for student in db.students.find():
            student.pop("_id", None)
            students.append(student)
        return students
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", dependencies=[Depends(get_current_user)])
async def add_student(student: Student):
    try:
        student_dict = student.dict()
        if await db.students.find_one({"id": student_dict["id"]}):
            raise HTTPException(status_code=400, detail="Student ID already exists")
        result = await db.students.insert_one(student_dict)
        return {"message": "Student added", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{id}", dependencies=[Depends(get_current_user)])
async def update_student(id: str, student: Student):
    try:
        student_dict = student.dict()
        result = await db.students.update_one({"id": id}, {"$set": student_dict})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"message": "Student updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", dependencies=[Depends(get_current_user)])
async def delete_student(id: str):
    try:
        result = await db.students.delete_one({"id": id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"message": "Student deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}/performance", dependencies=[Depends(get_current_user)])
async def get_student_performance(id: str):
    try:
        answers = []
        async for answer in db.answers.find({"studentId": id}):
            answer.pop("_id", None)
            answers.append(answer)
        return {"answers": answers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/performance-metrics", dependencies=[Depends(get_current_user)])
async def compute_performance_metrics(data: dict):
    try:
        answers = data.get("answers", [])
        total = len(answers)
        correct = sum(1 for a in answers if a["isCorrect"])
        overall_accuracy = correct / total if total > 0 else 0

        category_breakdown = defaultdict(lambda: {"totalQuestions": 0, "correct": 0})
        difficulty_breakdown = defaultdict(lambda: {"totalQuestions": 0, "correct": 0})

        for answer in answers:
            category = answer["category"]
            difficulty = answer["difficulty"]
            category_breakdown[category]["totalQuestions"] += 1
            difficulty_breakdown[difficulty]["totalQuestions"] += 1
            if answer["isCorrect"]:
                category_breakdown[category]["correct"] += 1
                difficulty_breakdown[difficulty]["correct"] += 1

        for category in category_breakdown:
            cb = category_breakdown[category]
            cb["accuracy"] = cb["correct"] / cb["totalQuestions"] if cb["totalQuestions"] > 0 else 0
        for difficulty in difficulty_breakdown:
            db = difficulty_breakdown[difficulty]
            db["accuracy"] = db["correct"] / db["totalQuestions"] if db["totalQuestions"] > 0 else 0

        return {
            "overallAccuracy": overall_accuracy,
            "categoryBreakdown": [{"category": k, **v} for k, v in category_breakdown.items()],
            "difficultyBreakdown": [{"difficulty": k, **v} for k, v in difficulty_breakdown.items()]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/time-spent", dependencies=[Depends(get_current_user)])
async def compute_time_spent(data: dict):
    try:
        answers = data.get("answers", [])
        total_time = sum(a.get("timeTaken", 0) for a in answers)
        total_questions = len(answers)
        avg_time = total_time / total_questions if total_questions > 0 else 0

        time_by_category = defaultdict(list)
        for answer in answers:
            time_by_category[answer["category"]].append(answer.get("timeTaken", 0))

        time_by_category_avg = [
            {"category": k, "averageTime": sum(v) / len(v) if v else 0}
            for k, v in time_by_category.items()
        ]

        return {
            "averageTimePerQuestion": avg_time,
            "byCategory": time_by_category_avg
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))