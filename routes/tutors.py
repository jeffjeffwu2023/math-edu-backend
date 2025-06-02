# routes/tutors.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from .auth import get_current_user

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/tutors", tags=["tutors"])

class AssignStudentsRequest(BaseModel):
    tutorId: str
    studentIds: list[str]

@router.post("/assign-students")
async def assign_students(request: AssignStudentsRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can assign students")
    
    # Validate tutor
    tutor = await db.users.find_one({"id": request.tutorId, "role": "tutor"})
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")
    
    # Validate students
    valid_students = await db.users.find({"id": {"$in": request.studentIds}, "role": "student"}).to_list(None)
    if len(valid_students) != len(request.studentIds):
        invalid_ids = set(request.studentIds) - {s["id"] for s in valid_students}
        raise HTTPException(status_code=404, detail=f"Students not found: {invalid_ids}")
    
    # Update students' tutorId
    await db.users.update_many(
        {"id": {"$in": request.studentIds}, "role": "student"},
        {"$set": {"tutorId": request.tutorId}}
    )
    
    # Update tutor's studentIds
    await db.users.update_one(
        {"id": request.tutorId, "role": "tutor"},
        {"$addToSet": {"studentIds": {"$each": request.studentIds}}}
    )
    
    return {"message": "Students assigned successfully"}