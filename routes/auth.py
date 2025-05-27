# routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt
import bcrypt
import os
from dotenv import load_dotenv

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
    user = await db.users.find_one({"id": user_id})
    return user

@router.post("/login")
async def login(request: LoginRequest):
    user = await get_user_by_id(request.id)
    if not user or not bcrypt.checkpw(request.password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = jwt.encode({"id": user["id"], "role": user["role"]}, JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "user": {"id": user["id"], "name": user["name"], "role": user["role"], "language": user["language"]}}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("id")
        role = payload.get("role")
        if not user_id or not role:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"id": user["id"], "role": user["role"], "name": user["name"], "language": user["language"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")