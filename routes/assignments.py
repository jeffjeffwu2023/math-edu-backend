from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from bson import ObjectId
from .auth import get_current_user
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/assignments", tags=["assignments"])

class AssignmentCreate(BaseModel):
  questionIndices: list[int]
  studentId: str

@router.post("/")
async def create_assignment(assignment: AssignmentCreate, current_user: dict = Depends(get_current_user)):
  if current_user["role"] not in ["admin", "tutor"]:
    raise HTTPException(403, "Only admins or tutors can create assignments")
  user = await db.users.find_one({"id": assignment.studentId, "role": "student"})
  if not user:
    raise HTTPException(404, "Student not found")
  if current_user["role"] == "tutor" and assignment.studentId not in current_user.get("studentIds", []):
    raise HTTPException(403, "Tutor not assigned to this student")
  assignment_dict = {
    "id": str(ObjectId()),
    "questionIndices": assignment.questionIndices,
    "studentId": assignment.studentId,
    "tutorId": current_user["id"],
    "submitted": False,
    "createdAt": datetime.utcnow()
  }
  await db.assignments.insert_one(assignment_dict)
  return assignment_dict

@router.get("/")
async def get_assignments(student_id: str = None, current_user: dict = Depends(get_current_user)):
  if current_user["role"] not in ["admin", "tutor"] and current_user["id"] != student_id:
    raise HTTPException(403, "Unauthorized access")
  query = {"studentId": student_id} if student_id else {}
  assignments = await db.assignments.find(query).to_list(None)
  return [
    {
      "id": assignment["id"],
      "questionIndices": assignment["questionIndices"],
      "studentId": assignment["studentId"],
      "tutorId": assignment.get("tutorId", ""),
      "submitted": assignment["submitted"],
      "createdAt": assignment["createdAt"]
    }
    for assignment in assignments
  ]

@router.put("/submit/{assignment_id}")
async def submit_assignment(assignment_id: str, current_user: dict = Depends(get_current_user)):
  if current_user["role"] != "student":
    raise HTTPException(403, "Only students can submit assignments")
  assignment = await db.assignments.find_one({"id": assignment_id})
  if not assignment or assignment["studentId"] != current_user["id"]:
    raise HTTPException(404, "Assignment not found or unauthorized")
  result = await db.assignments.update_one(
    {"id": assignment_id},
    {"$set": {"submitted": True}}
  )
  if result.modified_count == 0:
    raise HTTPException(400, "Failed to submit assignment")
  return {"message": "Assignment submitted"}