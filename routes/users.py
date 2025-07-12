# routes/users.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from bcrypt import hashpw, gensalt
import os
from dotenv import load_dotenv
from .auth import get_current_user
import logging
from pymongo.errors import DuplicateKeyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    disabled: bool = False  # Added for soft delete

class UserUpdate(BaseModel):
    name: str
    email: str
    role: str
    language: str = "en"
    tutorId: str = None
    studentIds: list[str] = []
    classroomIds: list[str] = []
    disabled: bool = None  # Optional for soft delete toggle

VALID_ROLES = {"student", "parent", "tutor", "manager", "admin"}

@router.get("/")
async def get_users(role: str = None, include_disabled: bool = False, current_user: dict = Depends(get_current_user)):
    # Validate role parameter
    if role and role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {', '.join(VALID_ROLES)}")
    
    # Build query
    query = {"role": role} if role else {}
    if not include_disabled:
        query["disabled"] = False  # Filter out disabled users by default
    
    users = await db.users.find(query).to_list(None)
    return [
        {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "language": user["language"],
            "tutorId": user.get("tutorId"),
            "studentIds": user.get("studentIds", []),
            "classroomIds": user.get("classroomIds", []),
            "disabled": user.get("disabled", False)  # Include disabled status
        }
        for user in users
    ]

@router.get("/bytutor/{tutor_id}")
async def get_users_by_tutor(tutor_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching users for tutor_id: {tutor_id}, current_user: {current_user}") 
    
    # Validate role parameter
    if current_user["role"] not in ["tutor"]:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    # Build query
    query = {"tutorId": tutor_id, "disabled": False}  # Filter out disabled students
    
    users = await db.users.find(query).to_list(None)
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

@router.get("/children/pid={parent_id}")
async def get_children_by_parent(parent_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching children for parent_id: {parent_id}, current_user: {current_user}")
    
    if current_user["role"] not in ["parent"]:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    if current_user["id"] != parent_id:
        raise HTTPException(status_code=403, detail="Cannot access another parent's children")
    
    children = []
    if "studentIds" in current_user and current_user["studentIds"]:
        children = await db.users.find({"id": {"$in": current_user["studentIds"]}, "role": "student", "disabled": False}).to_list(None)
    
    return [
        {
            "id": child["id"],
            "name": child["name"],
            "email": child["email"],
            "language": child["language"]
        }
        for child in children
    ]

@router.post("/")
async def add_user(user: UserCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add users")
    if await db.users.find_one({"id": user.id}):
        raise HTTPException(status_code=400, detail="User ID already exists")
    if user.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {', '.join(VALID_ROLES)}")
    if user.role == "student" and user.tutorId:
        tutor = await db.users.find_one({"id": user.tutorId, "role": "tutor", "disabled": False})
        if not tutor:
            raise HTTPException(status_code=400, detail="Tutor not found")
        await db.users.update_one(
            {"id": user.tutorId},
            {"$addToSet": {"studentIds": user.id}}
        )
    try:
        hashed_password = hashpw(user.password.encode("utf-8"), gensalt()).decode("utf-8")
        user_dict = user.dict()
        user_dict["password"] = hashed_password
        user_dict["performanceData"] = {"totalCorrect": 0, "totalAttempts": 0, "avgTimeTaken": 0.0}
        await db.users.insert_one(user_dict)
    except DuplicateKeyError as e:
        raise HTTPException(status_code=400, detail=f"Duplicate key error: {str(e)}")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "language": user.language,
        "tutorId": user.tutorId,
        "studentIds": user.studentIds,
        "classroomIds": user.classroomIds,
        "disabled": user.disabled
    }

@router.put("/{user_id}")
async def update_user(user_id: str, update_data: UserUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")
    if update_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {', '.join(VALID_ROLES)}")
    if update_data.role == "student" and update_data.tutorId:
        tutor = await db.users.find_one({"id": update_data.tutorId, "role": "tutor", "disabled": False})
        if not tutor:
            raise HTTPException(status_code=400, detail="Tutor not found")
        await db.users.update_one(
            {"id": update_data.tutorId},
            {"$addToSet": {"studentIds": user_id}}
        )
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data.dict(exclude_unset=True)}  # Only update provided fields
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated"}

@router.delete("/{user_id}")
async def soft_delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete users")
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"disabled": True}}  # Soft delete by setting disabled to true
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User soft deleted"}