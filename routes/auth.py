# routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter()

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Replace with a secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    id: str
    password: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    return user


@router.post("/login/")
async def login(request: LoginRequest):
    print(f"Login request: {request.id}")
    user = await get_user(request.id)
    print(f"User found: {user}")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    print(f"Verifying password: {request.password} against {user['password']}")
    try:
        if not pwd_context.verify(request.password, user["password"]):
            print("Password verification failed")
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except ValueError as e:
        print(f"Password verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Password verification error: {str(e)}")
    access_token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    print(f"Generated token: {access_token}")
    return {"access_token": access_token, "token_type": "bearer", "user": user}