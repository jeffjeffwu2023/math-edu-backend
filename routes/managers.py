from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/managers", tags=["managers"])

class ManagerAssignment(BaseModel):
  userId: str
  classroomId: str

@router.post("/")
async def assign_manager(assignment: ManagerAssignment):
  user = await db.users.find_one({"id": assignment.userId, "role": "manager"})
  if not user:
    raise HTTPException(404, "Manager not found")
  classroom = await db.classrooms.find_one({"id": assignment.classroomId})
  if not classroom:
    raise HTTPException(404, "Classroom not found")
  await db.classrooms.update_one(
    {"id": assignment.classroomId},
    {"$addToSet": {"managerIds": assignment.userId}}
  )
  await db.users.update_one(
    {"id": assignment.userId},
    {"$addToSet": {"classroomIds": assignment.classroomId}}
  )
  return {"message": "Manager assigned"}

@router.delete("/")
async def remove_manager(assignment: ManagerAssignment):
  classroom = await db.classrooms.find_one({"id": assignment.classroomId})
  if not classroom or assignment.userId not in classroom.get("managerIds", []):
    raise HTTPException(404, "Assignment not found")
  await db.classrooms.update_one(
    {"id": assignment.classroomId},
    {"$pull": {"managerIds": assignment.userId}}
  )
  await db.users.update_one(
    {"id": assignment.userId},
    {"$pull": {"classroomIds": assignment.classroomId}}
  )
  return {"message": "Manager removed"}

@router.get("/")
async def get_manager_assignments():
  classrooms = await db.classrooms.find({"managerIds": {"$exists": True}}).to_list(None)
  assignments = []
  for classroom in classrooms:
    for managerId in classroom.get("managerIds", []):
      assignments.append({"userId": managerId, "classroomId": classroom["id"]})
  return assignments