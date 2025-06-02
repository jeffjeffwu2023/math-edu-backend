# routes/performance.py
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from .auth import get_current_user
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/performance", tags=["performance"])

@router.get("/{student_id}")
async def analyze_student(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "tutor"] and current_user["id"] != student_id:
        raise HTTPException(403, "Unauthorized access")
    
    # Verify student exists
    user = await db.users.find_one({"id": student_id, "role": "student"})
    if not user:
        raise HTTPException(404, "Student not found")
    
    # Fetch performance data from users collection
    performance_data = user.get("performanceData", {
        "totalCorrect": 0,
        "totalAttempts": 0,
        "avgTimeTaken": 0.0
    })
    
    # Fetch answers for detailed analysis
    answers = await db.answers.find({"studentId": student_id}).to_list(None)
    
    # Calculate category-wise performance
    category_metrics = {}
    for answer in answers:
        question = await db.questions.find_one({"index": answer["questionIndex"]})
        category = question.get("category", "Unknown") if question else "Unknown"
        category_metrics[category] = category_metrics.get(category, {"correct": 0, "total": 0})
        category_metrics[category]["total"] += 1
        if answer["isCorrect"]:
            category_metrics[category]["correct"] += 1
    
    # Calculate accuracy per category
    for category in category_metrics:
        metrics = category_metrics[category]
        metrics["accuracy"] = (
            metrics["correct"] / metrics["total"] * 100 if metrics["total"] > 0 else 0
        )
    
    return {
        "studentId": student_id,
        "performanceData": performance_data,
        "categoryMetrics": category_metrics,
        "totalAnswers": len(answers)
    }