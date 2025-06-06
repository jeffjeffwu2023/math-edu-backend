# routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]
JWT_SECRET = os.getenv("JWT_SECRET")

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class LoginRequest(BaseModel):
    email: str
    password: str

async def get_user_by_id(user_id: str):
    logger.info(f"Fetching user with name: {user_id}")
    user = await db.users.find_one({"id": user_id})
    if user:
        logger.info(f"User found: {user['id']}, role: {user['role']}")
    else:
        logger.warning(f"User not found for name: {user_id}")
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        logger.info(f"Decoding token: {token}")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        logger.info(f"Payload: {payload}")  # Changed from error to info
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

@router.post("/login/")
async def login(request: LoginRequest):
    logger.info(f"Login attempt for email: {request.email}")
    logger.info(f"Password: {request.password}")  # Be cautious with logging passwords in production    
    
    user = await db.users.find_one({"email": request.email})
    
    if not user or not pwd_context.verify(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check for math-related roles
    math_roles = ["student", "tutor", "admin"]
    if user["role"] not in math_roles:
        raise HTTPException(status_code=403, detail="User does not have a math-related role")
    
    # Generate JWT token
    token = jwt.encode({"id": user["id"], "role": user["role"]}, os.getenv("JWT_SECRET"), algorithm="HS256")
    return {
        "access_token": token,
        "user": {
            "id": user["id"],
            "role": user["role"],
            "name": user["name"],
            "email": user["email"]
        }
    }

@router.get("/current-user")
async def get_current_user_endpoint(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "role": current_user["role"],
        "name": current_user["name"],
        "language": current_user["language"],
    }