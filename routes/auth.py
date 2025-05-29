# routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt
import bcrypt
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]
JWT_SECRET = os.getenv("JWT_SECRET")

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class LoginRequest(BaseModel):
    id: str
    password: str

async def get_user_by_id(user_id: str):
    logger.info(f"Fetching user with name: {user_id}")
    user = await db.users.find_one({"id": user_id})
    if user:
        logger.info(f"User found: {user['id']}, role: {user['role']}")
    else:
        logger.warning(f"User not found for name: {user_id}")
    return user

@router.post("/login")
async def login(request: LoginRequest):
    logger.info(f"Login attempt for user: {request.id}")
    user = await get_user_by_id(request.id)
    if not user:
        logger.error(f"Invalid credentials: User {request.id} not found")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.checkpw(request.password.encode("utf-8"), user["password"].encode("utf-8")):
        logger.error(f"Invalid credentials: Password mismatch for user {request.id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    logger.info(f"Login successful for user: {request.id}")
    token = jwt.encode({"id": user["id"], "role": user["role"]}, JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "user": {"id": user["id"], "name": user["name"], "role": user["role"], "language": user["language"], "tutorId": user["tutorId"], "studentIds": user["studentIds"], "classroomIds": user["classroomIds"]}}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("id")
        role = payload.get("role")
        if not user_id or not role:
            logger.error("Invalid token: Missing user_id or role")
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await get_user_by_id(user_id)
        if not user:
            logger.error(f"User not found for id: {user_id}")
            raise HTTPException(status_code=401, detail="User not found")
        return {"id": user["id"], "role": user["role"], "name": user["name"], "language": user["language"]}
    except JWTError as e:
        logger.error(f"JWTError: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")