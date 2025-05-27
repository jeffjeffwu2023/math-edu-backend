from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from bcrypt import hashpw, gensalt
import os
from dotenv import load_dotenv
from .auth import get_current_user

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/users", tags=["users"])

class UserCreate(BaseModel):
  id: str
  name: str
  email: str
  password: str
  role: str
  language: str = "en"
  tutorId: str = None
  studentIds: list[str] = []
  classroomIds: list[str] = []

class UserUpdate(BaseModel):
  name: str
  email: str
  role: str
  language: str = "en"
  tutorId: str = None
  studentIds: list[str] = []
  classroomIds: list[str] = []

@router.get("/")
async def get_users(current_user: dict = Depends(get_current_user)):
  if current_user["role"] not in ["admin", "tutor"]:
    raise HTTPException(status_code=403, detail="Unauthorized access")
  users = await db.users.find().to_list(None)
  return [
    {
      "id": user["id"],
      "name": user["name"],
      "email": user["email"],
      "role": user["role"],
      "language": user["language"],
      "tutorId": user.get("tutorId"),
      "studentIds": user.get("studentIds", []),
      "classroomIds": user.get("classroomIds", [])
    }
    for user in users
  ]

@router.post("/")
async def add_user(user: UserCreate, current_user: dict = Depends(get_current_user)):
  if current_user["role"] != "admin":
    raise HTTPException(status_code=403, detail="Only admins can add users")
  if await db.users.find_one({"id": user.id}):
    raise HTTPException(status_code=400, detail="User ID already exists")
  if user.role not in ["student", "parent", "tutor", "manager", "admin"]:
    raise HTTPException(status_code=400, detail="Invalid role")
  if user.role == "student" and user.tutorId:
    tutor = await db.users.find_one({"id": user.tutorId, "role": "tutor"})
    if not tutor:
      raise HTTPException(status_code=400, detail="Tutor not found")
    await db.users.update_one(
      {"id": user.tutorId},
      {"$addToSet": {"studentIds": user.id}}
    )
  hashed_password = hashpw(user.password.encode("utf-8"), gensalt()).decode("utf-8")
  user_dict = user.dict()
  user_dict["password"] = hashed_password
  user_dict["performanceData"] = {"totalCorrect": 0, "totalAttempts": 0, "avgTimeTaken": 0.0}
  await db.users.insert_one(user_dict)
  return {
    "id": user.id,
    "name": user.name,
    "email": user.email,
    "role": user.role,
    "language": user.language,
    "tutorId": user.tutorId,
    "studentIds": user.studentIds,
    "classroomIds": user.classroomIds
  }

@router.put("/{user_id}")
async def update_user(user_id: str, update_data: UserUpdate, current_user: dict = Depends(get_current_user)):
  if current_user["role"] != "admin":
    raise HTTPException(status_code=403, detail="Only admins can update users")
  if update_data.role not in ["student", "parent", "tutor", "manager", "admin"]:
    raise HTTPException(status_code=400, detail="Invalid role")
  if update_data.role == "student" and update_data.tutorId:
    tutor = await db.users.find_one({"id": update_data.tutorId, "role": "tutor"})
    if not tutor:
      raise HTTPException(status_code=400, detail="Tutor not found")
    await db.users.update_one(
      {"id": update_data.tutorId},
      {"$addToSet": {"studentIds": user_id}}
    )
  result = await db.users.update_one(
    {"id": user_id},
    {"$set": update_data.dict()}
  )
  if result.modified_count == 0:
    raise HTTPException(status_code=404, detail="User not found")
  return {"message": "User updated"}

@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
  if current_user["role"] != "admin":
    raise HTTPException(status_code=403, detail="Only admins can delete users")
  result = await db.users.delete_one({"id": user_id})
  if result.deleted_count == 0:
    raise HTTPException(status_code=404, detail="User not found")
  return {"message": "User deleted"}