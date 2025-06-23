# routes/question_generator.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from routes.auth import get_current_user
import logging
from routes.grok_math_handler import process_math_question
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate-question", tags=["question-generator"])

class GenerateQuestionRequest(BaseModel):
    difficulty: str  # "easy", "medium", "hard"
    topic: str = None  # "algebra", "geometry", "calculus", or None for random
    save_to_db: bool = False  # Option to save to MongoDB
    ai_provider: str = None  # New field to switch between providers, default to grok

@router.post("/", response_model=dict)  # Matches the dictionary structure
async def generate_question(request: GenerateQuestionRequest, current_user: dict = Depends(get_current_user)):
    if request.ai_provider == "grok":
        return await process_math_question(request)  # Await the coroutine
    elif request.ai_provider == "openai":
        from routes.question_generator_openai import generate_question_openai
        return await generate_question_openai(request, current_user)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported AI provider: {request.ai_provider}")